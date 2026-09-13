from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
import logging

from .models import AttendanceSession
from .serializers import (
    AttendanceSessionSerializer,
    EndAttendanceSerializer,
    SessionStatusSerializer,
)
from accounts.permissions import IsIntern, IsTeamLeadOrAdmin
from notifications.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


def fmt_duration(td):
    if td is None:
        return '00:00:00'
    total = int(td.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# INTERN — start / continue

class StartAttendanceView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsIntern]
    serializer_class = AttendanceSessionSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()

        completed = AttendanceSession.objects.filter(
            user=user, date=today, status='completed'
        ).first()
        if completed:
            return Response(
                {'error': 'You have already ended your duty for today.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session, is_new, message = AttendanceSession.handle_intern_login(
            user, allow_relogin=True
        )
        return Response({
            'is_new': is_new,
            'message': message,
            'session': AttendanceSessionSerializer(session).data
        }, status=status.HTTP_200_OK if not is_new else status.HTTP_201_CREATED)


# INTERN — end duty

class EndAttendanceView(generics.GenericAPIView):
    """End Duty — CLOSES the session permanently for the day."""
    permission_classes = [permissions.IsAuthenticated, IsIntern]
    serializer_class = EndAttendanceSerializer

    def post(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()

        try:
            session = AttendanceSession.objects.get(
                user=user, date=today, status='active'
            )
        except AttendanceSession.DoesNotExist:
            return Response(
                {'error': 'No active session found for today.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        daily_summary = serializer.validated_data['daily_summary']

        active_break = session.breaks.filter(status='active').first()
        if active_break:
            active_break.end_break()

        pending = session.availability_checks.filter(status='pending').first()
        if pending:
            pending.auto_miss_if_expired()
            if pending.status == 'pending':
                pending.mark_missed(notify=False)

        session.close_session(daily_summary=daily_summary)

        return Response({
            'message': 'Duty ended for today.',
            'session': AttendanceSessionSerializer(session).data
        })


# INTERN — current

class CurrentAttendanceView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SessionStatusSerializer

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role != 'intern':
            return Response({
                'has_session': False, 'is_new': False,
                'message': 'Only interns have attendance sessions.',
                'session': None
            })

        today = timezone.now().date()
        totals = AttendanceSession.daily_totals(user, today)

        def build_payload(session, is_new, message):
            return {
                'has_session': True,
                'is_new': is_new,
                'message': message,
                'session': AttendanceSessionSerializer(session).data,
                'day_total_duration': str(totals['total_duration']),
                'day_total_break': str(totals['total_break']),
                'day_total_working': str(totals['working_time']),
                'completed_today_duration': str(totals['completed_duration']),
                'session_count': totals['session_count'],
            }

        # 1. Active
        session = AttendanceSession.objects.filter(
            user=user, date=today, status='active'
        ).first()
        if session:
            return Response(build_payload(
                session, False,
                f"Session active. Login #{session.login_count} today."
            ))

        # 2. Completed today
        completed = AttendanceSession.objects.filter(
            user=user, date=today, status='completed'
        ).first()
        if completed:
            return Response(build_payload(
                completed, False, 'Your duty for today is done.'
            ))

        # 3. Paused today
        paused = AttendanceSession.objects.filter(
            user=user, date=today, status='paused'
        ).order_by('-login_time').first()
        if paused:
            return Response(build_payload(
                paused, False, 'Session paused.'
            ))

        # 4. Force logged out today
        forced = AttendanceSession.objects.filter(
            user=user, date=today, status='force_logged_out'
        ).order_by('-login_time').first()
        if forced:
            return Response(build_payload(
                forced, False,
                'You were logged out by your Team Lead. Log in again to continue.'
            ))

        # 5. Fresh session
        session, is_new, message = AttendanceSession.handle_intern_login(user)
        totals = AttendanceSession.daily_totals(user, today)
        return Response(build_payload(session, is_new, message))


# INTERN — history

class AttendanceHistoryView(generics.ListAPIView):
    serializer_class = AttendanceSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AttendanceSession.objects.filter(
            user=self.request.user
        ).order_by('-login_time')


# LEAD — all sessions

class AllAttendanceView(generics.ListAPIView):
    serializer_class = AttendanceSessionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def get_queryset(self):
        queryset = AttendanceSession.objects.all().order_by('-login_time')
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(date=date)
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset


# LEAD — daily summary

class DailyAttendanceSummaryView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def get(self, request, *args, **kwargs):
        date_str = request.query_params.get('date')
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        interns = User.objects.filter(role='intern', is_active=True)
        rows = []

        for intern in interns:
            sessions = list(AttendanceSession.objects.filter(
                user=intern, date=target_date
            ).order_by('login_time'))

            if not sessions:
                rows.append({
                    'user_id': intern.id,
                    'username': intern.username,
                    'full_name': intern.get_full_name() or intern.username,
                    'date': str(target_date),
                    'login': None,
                    'logout': None,
                    'total_duration': '00:00:00',
                    'total_break': '00:00:00',
                    'total_working': '00:00:00',
                    'total_logins': 0,
                    'session_count': 0,
                    'status': 'no_activity',
                })
                continue

            total_duration = timedelta(0)
            total_break = timedelta(0)
            total_logins = 0
            for s in sessions:
                total_duration += s.duration
                total_break += s.total_break_time
                total_logins += (s.login_count or 0)

            first_session = sessions[0]
            last_session = sessions[-1]

            if any(s.status == 'active' for s in sessions):
                status_value = 'active'
            elif last_session.status == 'force_logged_out':
                status_value = 'force_logged_out'
            elif last_session.status == 'paused':
                status_value = 'paused'
            else:
                status_value = 'completed'

            rows.append({
                'user_id': intern.id,
                'username': intern.username,
                'full_name': intern.get_full_name() or intern.username,
                'date': str(target_date),
                'login': first_session.login_time.strftime('%I:%M %p'),
                'logout': last_session.logout_time.strftime('%I:%M %p') if last_session.logout_time else None,
                'total_duration': fmt_duration(total_duration),
                'total_break': fmt_duration(total_break),
                'total_working': fmt_duration(total_duration - total_break),
                'total_logins': total_logins,
                'session_count': len(sessions),
                'status': status_value,
            })

        rows.sort(key=lambda r: (
            0 if r['status'] == 'active' else
            1 if r['status'] == 'paused' else
            2 if r['status'] == 'force_logged_out' else
            3 if r['status'] == 'completed' else 4,
            r['username']
        ))

        return Response({
            'date': str(target_date),
            'rows': rows,
            'total_interns': len(rows),
        })


# LEAD — force logout

class ForceLogoutView(generics.GenericAPIView):
    """
    POST /api/attendance/force-logout/{user_id}/

    Force-logs-out an intern:
      1. Closes the attendance session (active OR paused)
      2. Deletes ALL Django sessions for that user → kicks them off the web app
      3. Sends a notification
    """
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def post(self, request, user_id, *args, **kwargs):
        from django.contrib.sessions.models import Session

        # 1. Find the intern
        try:
            intern = User.objects.get(pk=user_id, role='intern')
        except User.DoesNotExist:
            return Response(
                {'error': 'Intern not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. Find their active OR paused session
        session = AttendanceSession.objects.filter(
            user=intern, status__in=['active', 'paused']
        ).order_by('-login_time').first()
        if not session:
            return Response(
                {'error': 'This intern has no active or paused session.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. End active break
        active_break = session.breaks.filter(status='active').first()
        if active_break:
            active_break.end_break()

        # 4. Resolve pending availability check
        pending = session.availability_checks.filter(status='pending').first()
        if pending:
            pending.auto_miss_if_expired()
            if pending.status == 'pending':
                pending.mark_missed(notify=False)

        # 5. Force logout the attendance session
        reason = request.data.get('reason', 'Force logged out by Team Lead')
        session.force_logout(reason=reason)

        # 6. Delete ALL Django sessions for this user
        #    This logs them out at the session level — every browser/tab.
        deleted_count = 0
        for s in Session.objects.all():
            try:
                data = s.get_decoded()
                if data.get('_auth_user_id') == str(intern.id):
                    s.delete()
                    deleted_count += 1
            except Exception:
                continue

        logger.info(
            f"Force logout: {intern.username} — attendance session #{session.id} closed, "
            f"{deleted_count} Django session(s) deleted."
        )

        # 7. Notify the intern
        try:
            Notification.objects.create(
                recipient=intern,
                sender=request.user,
                notification_type='system',
                message=(
                    f'You were logged out by {request.user.username}. '
                    f'Reason: {reason}'
                ),
                related_object_id=session.id,
                related_object_type='AttendanceSession',
            )
        except Exception:
            pass

        return Response({
            'message': f'{intern.username} has been logged out.',
            'session': AttendanceSessionSerializer(session).data,
            'django_sessions_deleted': deleted_count,
        })