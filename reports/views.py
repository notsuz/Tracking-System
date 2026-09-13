from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta, datetime

from accounts.permissions import IsTeamLeadOrAdmin
from attendance.models import AttendanceSession
from breaks.models import Break
from tasks.models import Task
from availability.models import AvailabilityCheck
from django.contrib.auth import get_user_model

User = get_user_model()


# Helpers

def fmt_duration(td):
    """Format a timedelta as HH:MM:SS."""
    if td is None:
        return '00:00:00'
    total = int(td.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_time(dt, fmt='%H:%M', fallback='—'):
    """
    Format a datetime. When USE_TZ=False, dt is already local time,
    so we just strftime it directly.
    """
    if not dt:
        return fallback
    return dt.strftime(fmt)


def fmt_date(dt, fmt='%Y-%m-%d', fallback='—'):
    if not dt:
        return fallback
    return dt.strftime(fmt)


# Daily Report

class DailyReportView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def get(self, request, *args, **kwargs):
        date = request.query_params.get('date')
        if date:
            report_date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            report_date = timezone.now().date()

        sessions = AttendanceSession.objects.filter(date=report_date)

        total_interns = sessions.values('user').distinct().count()
        active_sessions = sessions.filter(status='active').count()
        completed_sessions = sessions.filter(status='completed').count()
        force_logged_out = sessions.filter(status='force_logged_out').count()

        total_duration = timedelta(0)
        total_break_time = timedelta(0)
        for s in sessions:
            total_duration += s.duration
            total_break_time += s.total_break_time

        tasks = Task.objects.filter(created_at__date=report_date)
        tasks_assigned = tasks.count()
        tasks_completed = tasks.filter(status='completed').count()
        tasks_in_progress = tasks.filter(status='in_progress').count()

        availability_checks = AvailabilityCheck.objects.filter(
            created_at__date=report_date
        )
        total_checks = availability_checks.count()
        responded_checks = availability_checks.filter(status='responded').count()
        missed_checks = availability_checks.filter(status='missed').count()

        # ---------- Per-intern breakdown ----------
        intern_breakdown = []
        for s in sessions:
            intern = s.user
            intern_tasks = tasks.filter(assigned_to=intern)
            intern_breakdown.append({
                'user_id': intern.id,
                'username': intern.username,
                'full_name': intern.get_full_name() or intern.username,
                'login_time': fmt_time(s.login_time),
                'logout_time': fmt_time(s.logout_time),
                'duration': fmt_duration(s.duration),
                'break_time': fmt_duration(s.total_break_time),
                'working_time': fmt_duration(s.working_time),
                'login_count': s.login_count,
                'status': s.status,
                'tasks_assigned': intern_tasks.count(),
                'tasks_completed': intern_tasks.filter(status='completed').count(),
            })

        return Response({
            'date': str(report_date),
            'attendance': {
                'total_interns': total_interns,
                'active_sessions': active_sessions,
                'completed_sessions': completed_sessions,
                'force_logged_out': force_logged_out,
                'total_duration': fmt_duration(total_duration),
                'total_break_time': fmt_duration(total_break_time),
                'total_working_time': fmt_duration(total_duration - total_break_time),
            },
            'tasks': {
                'assigned': tasks_assigned,
                'completed': tasks_completed,
                'in_progress': tasks_in_progress,
                'completion_rate': (
                    f"{(tasks_completed / tasks_assigned * 100):.2f}%"
                    if tasks_assigned > 0 else "0.00%"
                ),
            },
            'availability': {
                'total_checks': total_checks,
                'responded': responded_checks,
                'missed': missed_checks,
                'response_rate': (
                    f"{(responded_checks / total_checks * 100):.2f}%"
                    if total_checks > 0 else "0.00%"
                ),
            },
            'intern_breakdown': intern_breakdown,
        })


# Intern Report

class InternReportView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        sessions = AttendanceSession.objects.filter(user=user)
        if start_date:
            sessions = sessions.filter(date__gte=start_date)
        if end_date:
            sessions = sessions.filter(date__lte=end_date)

        total_sessions = sessions.count()
        completed_sessions = sessions.filter(status='completed').count()

        total_duration = timedelta(0)
        total_break_time = timedelta(0)
        for s in sessions:
            total_duration += s.duration
            total_break_time += s.total_break_time

        tasks = Task.objects.filter(assigned_to=user)
        if start_date:
            tasks = tasks.filter(created_at__date__gte=start_date)
        if end_date:
            tasks = tasks.filter(created_at__date__lte=end_date)

        total_tasks = tasks.count()
        completed_tasks = tasks.filter(status='completed').count()

        availability_checks = AvailabilityCheck.objects.filter(
            attendance_session__user=user
        )
        if start_date:
            availability_checks = availability_checks.filter(
                created_at__date__gte=start_date
            )
        if end_date:
            availability_checks = availability_checks.filter(
                created_at__date__lte=end_date
            )

        total_checks = availability_checks.count()
        responded_checks = availability_checks.filter(status='responded').count()

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'name': user.get_full_name(),
                'email': user.email,
                'role': user.role,
            },
            'date_range': {'start_date': start_date, 'end_date': end_date},
            'attendance': {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'total_duration': fmt_duration(total_duration),
                'total_break_time': fmt_duration(total_break_time),
                'total_working_time': fmt_duration(total_duration - total_break_time),
                'average_duration': (
                    fmt_duration(total_duration / total_sessions)
                    if total_sessions > 0 else "00:00:00"
                ),
            },
            'tasks': {
                'total': total_tasks,
                'completed': completed_tasks,
                'completion_rate': (
                    f"{(completed_tasks / total_tasks * 100):.2f}%"
                    if total_tasks > 0 else "0.00%"
                ),
            },
            'availability': {
                'total_checks': total_checks,
                'responded': responded_checks,
                'response_rate': (
                    f"{(responded_checks / total_checks * 100):.2f}%"
                    if total_checks > 0 else "0.00%"
                ),
            },
        })


# Current Status (Team Lead — Interns page)

class CurrentStatusView(generics.GenericAPIView):
    """Live status of every active intern."""
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def get(self, request, *args, **kwargs):
        # Step 1: Auto-resolve any expired pending checks across the board
        for stale in AvailabilityCheck.objects.filter(status='pending'):
            stale.auto_miss_if_expired()

        # Step 2: Build the live response
        interns = User.objects.filter(role='intern', is_active=True)
        status_data = []

        for intern in interns:
            session = AttendanceSession.objects.filter(
                user=intern, status='active'
            ).first()

            # ---------- OFFLINE intern ----------
            if not session:
                last_session = AttendanceSession.objects.filter(
                    user=intern
                ).order_by('-login_time').first()

                last_check = None
                if last_session:
                    last_check = AvailabilityCheck.objects.filter(
                        attendance_session=last_session
                    ).order_by('-created_at').first()

                status_data.append({
                    'id': intern.id,
                    'username': intern.username,
                    'name': intern.get_full_name() or intern.username,
                    'email': intern.email,
                    'status': 'offline',
                    'login_time': None,
                    'duration': '00:00:00',
                    'break_duration': '00:00:00',
                    'on_break': False,
                    'break_start': None,
                    'login_count': last_session.login_count if last_session else 0,
                    'pending_check': False,
                    'last_check_status': last_check.status if last_check else None,
                })
                continue

            # ---------- ONLINE intern ----------
            current_break = Break.objects.filter(
                attendance_session=session, status='active'
            ).first()

            pending = AvailabilityCheck.objects.filter(
                attendance_session=session, status='pending'
            ).order_by('-created_at').first()

            # This should already be resolved from Step 1, but double-check
            if pending:
                pending.auto_miss_if_expired()
                if pending.status != 'pending':
                    pending = None

            last_resolved = AvailabilityCheck.objects.filter(
                attendance_session=session
            ).exclude(status='pending').order_by('-created_at').first()

            if pending:
                last_check_status = 'pending'
            elif last_resolved:
                last_check_status = last_resolved.status
            else:
                last_check_status = None

            status_data.append({
                'id': intern.id,
                'username': intern.username,
                'name': intern.get_full_name() or intern.username,
                'email': intern.email,
                'status': 'on_break' if current_break else 'active',
                'login_time': fmt_time(session.login_time),
                'duration': fmt_duration(session.duration),
                'break_duration': fmt_duration(session.total_break_time),
                'on_break': bool(current_break),
                'break_start': fmt_time(current_break.start_time) if current_break else None,
                'login_count': session.login_count,
                'pending_check': bool(pending),
                'last_check_status': last_check_status,
            })

        return Response({
            'total_interns': len(status_data),
            'active_interns': sum(
                1 for s in status_data
                if s['status'] in ['active', 'on_break']
            ),
            'online_interns': sum(
                1 for s in status_data if s['status'] == 'active'
            ),
            'on_break_interns': sum(
                1 for s in status_data if s['status'] == 'on_break'
            ),
            'offline_interns': sum(
                1 for s in status_data if s['status'] == 'offline'
            ),
            'interns': status_data,
        })