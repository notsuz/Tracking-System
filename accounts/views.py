from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, login as django_login, logout as django_logout
from django.utils import timezone
from django.db import models
from datetime import timedelta

from .models import User
from .serializers import (
    UserSerializer, LoginSerializer, ChangePasswordSerializer,
    CreateUserSerializer, AdminResetPasswordSerializer, AdminUpdateUserSerializer,
)
from .permissions import IsSuperAdmin

User = get_user_model()


# ==================== AUTH ====================

class LoginView(generics.GenericAPIView):
    """Login with username OR email. Returns JWT and creates Django session."""
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        django_login(
            request, user,
            backend='django.contrib.auth.backends.ModelBackend'
        )

        if user.role == 'intern':
            try:
                from attendance.models import AttendanceSession
                AttendanceSession.handle_intern_login(user, allow_relogin=True)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Attendance creation on login failed for {user.username}: {e}"
                )

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
            'must_change_password': user.must_change_password,
        })


class LogoutView(generics.GenericAPIView):
    """API Logout: pauses intern session, blacklists JWT, ends Django session."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        if user.is_authenticated and user.role == 'intern':
            try:
                from attendance.models import AttendanceSession
                today = timezone.now().date()
                session = AttendanceSession.objects.filter(
                    user=user, date=today, status='active'
                ).first()
                if session:
                    active_break = session.breaks.filter(status='active').first()
                    if active_break:
                        active_break.end_break()
                    session.pause_session(reason='Logged out via API')
            except Exception:
                pass

        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                RefreshToken(refresh_token).blacklist()
        except Exception:
            pass

        django_logout(request)
        return Response({'message': 'Logged out.'}, status=status.HTTP_200_OK)


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': 'Password changed successfully. Please log in again.'},
            status=status.HTTP_200_OK
        )


# ==================== SUPER ADMIN ====================

class AdminUserListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    serializer_class = UserSerializer

    def get_queryset(self):
        qs = User.objects.all().order_by('-date_joined')
        role = self.request.query_params.get('role')
        search = self.request.query_params.get('search')
        if role:
            qs = qs.filter(role=role)
        if search:
            qs = qs.filter(username__icontains=search) | qs.filter(email__icontains=search)
        return qs


class AdminCreateUserView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    serializer_class = CreateUserSerializer
    queryset = User.objects.all()


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    serializer_class = AdminUpdateUserSerializer
    queryset = User.objects.all()

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.is_superuser:
            return Response({'error': 'Cannot delete a superuser.'}, status=status.HTTP_400_BAD_REQUEST)
        if user == request.user:
            return Response({'error': 'You cannot delete yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminResetUserPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    serializer_class = AdminResetPasswordSerializer

    def post(self, request, pk, *args, **kwargs):
        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.context['target_user'] = target_user
        serializer.save()

        return Response({
            'message': f"Password reset for {target_user.username}. "
                       f"They will be asked to change it on next login."
        })


class AdminOverviewView(generics.GenericAPIView):
    """GET /api/accounts/admin/overview/ — aggregated analytics for admin dashboard."""
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request, *args, **kwargs):
        from attendance.models import AttendanceSession
        from tasks.models import Task
        from availability.models import AvailabilityCheck

        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=6)

        users_qs = User.objects.filter(is_active=True)
        admin_count = users_qs.filter(
            models.Q(role='admin') | models.Q(is_superuser=True)
        ).distinct().count()

        user_counts = {
            'total': users_qs.count(),
            'interns': users_qs.filter(role='intern').count(),
            'team_leads': users_qs.filter(role='team_lead').count(),
            'admins': admin_count,
        }

        today_sessions = AttendanceSession.objects.filter(date=today)
        today_active = today_sessions.filter(status='active').count()

        today_duration = timedelta(0)
        today_break = timedelta(0)
        for s in today_sessions:
            today_duration += s.duration
            today_break += s.total_break_time

        today_tasks_completed = Task.objects.filter(completed_at__date=today).count()

        week_sessions = AttendanceSession.objects.filter(date__gte=week_ago, date__lte=today)
        week_duration = timedelta(0)
        week_break = timedelta(0)
        for s in week_sessions:
            week_duration += s.duration
            week_break += s.total_break_time

        week_tasks_assigned = Task.objects.filter(created_at__date__gte=week_ago).count()
        week_tasks_completed = Task.objects.filter(completed_at__date__gte=week_ago).count()

        avail = AvailabilityCheck.objects.filter(created_at__date__gte=week_ago)
        total_checks = avail.count()
        responded = avail.filter(status='responded').count()
        missed = avail.filter(status='missed').count()
        response_rate = (
            f"{(responded / total_checks * 100):.0f}%"
            if total_checks > 0 else "0%"
        )

        def fmt_td(td):
            if td is None:
                return '00:00'
            total = int(td.total_seconds())
            h = total // 3600
            m = (total % 3600) // 60
            return f"{h:02d}:{m:02d}"

        return Response({
            'users': user_counts,
            'today': {
                'online': today_active,
                'total_duration': fmt_td(today_duration),
                'total_break': fmt_td(today_break),
                'tasks_completed': today_tasks_completed,
            },
            'week': {
                'total_duration': fmt_td(week_duration),
                'total_break': fmt_td(week_break),
                'tasks_assigned': week_tasks_assigned,
                'tasks_completed': week_tasks_completed,
            },
            'availability': {
                'total_checks': total_checks,
                'responded': responded,
                'missed': missed,
                'response_rate': response_rate,
            },
        })


class AdminTeamLeadsView(generics.GenericAPIView):
    """GET /api/accounts/admin/team-leads/ — live status of team leads."""
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get(self, request, *args, **kwargs):
        from attendance.models import AttendanceSession
        from tasks.models import Task

        leads = User.objects.filter(role='team_lead', is_active=True).order_by('username')
        today = timezone.now().date()
        rows = []

        for lead in leads:
            session = AttendanceSession.objects.filter(
                user=lead, date=today, status='active'
            ).first()

            tasks_created_today = Task.objects.filter(
                assigned_by=lead, created_at__date=today
            ).count()

            tasks_created_total = Task.objects.filter(assigned_by=lead).count()

            rows.append({
                'id': lead.id,
                'username': lead.username,
                'name': lead.get_full_name() or lead.username,
                'email': lead.email,
                'is_online': bool(session),
                'login_time': session.login_time.strftime('%I:%M %p') if session else None,
                'last_login': lead.last_login.strftime('%Y-%m-%d %I:%M %p') if lead.last_login else None,
                'tasks_created_today': tasks_created_today,
                'tasks_created_total': tasks_created_total,
            })

        return Response({'leads': rows, 'total': len(rows)})


class AdminAllTasksView(generics.ListAPIView):
    """GET /api/accounts/admin/all-tasks/ — every task in the system."""
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def get_serializer_class(self):
        from tasks.serializers import TaskSerializer
        return TaskSerializer

    def get_queryset(self):
        from tasks.models import Task
        qs = Task.objects.all().order_by('-created_at')

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)

        assigned_to = self.request.query_params.get('assigned_to')
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)

        return qs