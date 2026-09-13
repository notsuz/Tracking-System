from django.views.generic import TemplateView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import redirect
from django.contrib.auth import logout as django_logout
from django.contrib.auth import login as django_login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


# Base protected views

class LoginRequiredTemplateView(LoginRequiredMixin, TemplateView):
    login_url = '/login/'
    redirect_field_name = 'next'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{self.login_url}?next={request.path}')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['user_data'] = {
            "isAuthenticated": self.request.user.is_authenticated,
            "role": getattr(self.request.user, "role", ""),
            "id": self.request.user.id if self.request.user.is_authenticated else None,
            "username": self.request.user.username if self.request.user.is_authenticated else "",
            "email": self.request.user.email if self.request.user.is_authenticated else "",
            "fullName": self.request.user.get_full_name() if self.request.user.is_authenticated else "",
            "mustChangePassword": getattr(self.request.user, "must_change_password", False),
        }
        return context


class SuperAdminRequiredTemplateView(LoginRequiredTemplateView):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        if not (request.user.role == 'admin' or request.user.is_superuser):
            if request.user.role == 'intern':
                return redirect('dashboard')
            if request.user.role == 'team_lead':
                return redirect('lead_dashboard')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


# Home routing

class RoleBasedHomeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')
        user = request.user
        if user.role == 'intern':
            return redirect('dashboard')
        if user.role == 'team_lead':
            return redirect('lead_dashboard')
        if user.role == 'admin' or user.is_superuser:
            return redirect('admin_panel_dashboard')
        return redirect('login')


# Login / Logout

class CustomLoginView(DjangoLoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if user.role == 'intern':
            try:
                from attendance.models import AttendanceSession
                AttendanceSession.handle_intern_login(user, allow_relogin=True)
            except Exception as e:
                logger.error(f"Attendance creation on login failed for {user.username}: {e}")
        return response

    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or user.role == 'admin':
            return '/admin-panel/'
        if user.role == 'team_lead':
            return '/lead/dashboard/'
        if user.role == 'intern':
            return '/dashboard/'
        return '/'


class CustomLogoutView(View):
    """
    Sidebar Logout:
      - Pauses the intern's active attendance session (not completes it)
      - Ends the Django session
      - Redirects to /login/
    """
    def get(self, request):
        return self._do_logout(request)

    def post(self, request):
        return self._do_logout(request)

    def _do_logout(self, request):
        user = request.user

        if user.is_authenticated and getattr(user, 'role', '') == 'intern':
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

                    pending = session.availability_checks.filter(status='pending').first()
                    if pending:
                        pending.auto_miss_if_expired()
                        if pending.status == 'pending':
                            pending.mark_missed(notify=False)

                    session.pause_session(reason='Logged out by user')
                    logger.info(f"Paused session #{session.id} for {user.username}")
            except Exception as e:
                logger.error(f"Failed to pause attendance session on logout: {e}")

        django_logout(request)
        return redirect('login')


# Admin Panel page views

class AdminPanelTasksView(SuperAdminRequiredTemplateView):
    template_name = 'admin_panel/tasks.html'


class AdminPanelInternsView(SuperAdminRequiredTemplateView):
    template_name = 'admin_panel/interns.html'


class AdminPanelAttendanceView(SuperAdminRequiredTemplateView):
    template_name = 'admin_panel/attendance.html'


class AdminPanelTeamLeadsView(SuperAdminRequiredTemplateView):
    template_name = 'admin_panel/team_leads.html'


# API: session login (JWT → Django session)

@csrf_exempt
def session_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            if not user_id:
                return JsonResponse({'success': False, 'error': 'user_id required'}, status=400)

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

            if not user.is_active:
                return JsonResponse({'success': False, 'error': 'Account disabled'}, status=403)

            django_login(request, user)

            attendance_info = None
            if user.role == 'intern':
                from attendance.models import AttendanceSession
                from attendance.serializers import AttendanceSessionSerializer
                session, is_new, message = AttendanceSession.handle_intern_login(
                    user, allow_relogin=True
                )
                attendance_info = {
                    'session': AttendanceSessionSerializer(session).data,
                    'is_new': is_new,
                    'message': message,
                }

            return JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'fullName': user.get_full_name(),
                    'mustChangePassword': user.must_change_password,
                },
                'attendance': attendance_info,
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Session login error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)