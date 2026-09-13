from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import AvailabilityCheck
from .serializers import (
    AvailabilityCheckSerializer,
    SendAvailabilityCheckSerializer,
)
from accounts.permissions import IsIntern, IsTeamLeadOrAdmin
from attendance.models import AttendanceSession
from notifications.models import Notification

User = get_user_model()


# LEAD — send check(s) to one or more interns

class SendAvailabilityCheckView(generics.GenericAPIView):
    """
    Team Lead / Admin sends availability check(s) to one or more interns.
    """
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]
    serializer_class = SendAvailabilityCheckSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_ids = serializer.validated_data['user_ids']

        created = []
        errors = []

        for uid in user_ids:
            try:
                intern = User.objects.get(id=uid, role='intern')
            except User.DoesNotExist:
                errors.append({'user_id': uid, 'error': 'Intern not found.'})
                continue

            session = AttendanceSession.objects.filter(
                user=intern, status='active'
            ).first()
            if not session:
                errors.append({
                    'user_id': uid,
                    'username': intern.username,
                    'error': 'Intern is offline.',
                })
                continue

            # Auto-resolve any expired pending check
            existing = AvailabilityCheck.objects.filter(
                attendance_session=session, status='pending'
            ).first()
            if existing:
                if existing.auto_miss_if_expired():
                    existing = None

            if existing:
                errors.append({
                    'user_id': uid,
                    'username': intern.username,
                    'error': 'Intern already has a pending check.',
                })
                continue

            check = AvailabilityCheck.objects.create(
                attendance_session=session,
                status='pending',
            )
            created.append(check)

            Notification.objects.create(
                recipient=intern,
                sender=request.user,
                notification_type='system',
                message='Availability check requested by your Team Lead. Please respond.',
                related_object_id=check.id,
                related_object_type='AvailabilityCheck',
            )

        return Response({
            'created': AvailabilityCheckSerializer(created, many=True).data,
            'created_count': len(created),
            'errors': errors,
            'error_count': len(errors),
        }, status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST)


# INTERN — fetch the current pending check

class PendingAvailabilityView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsIntern]
    serializer_class = AvailabilityCheckSerializer

    def get(self, request, *args, **kwargs):
        session = AttendanceSession.objects.filter(
            user=request.user, status='active'
        ).first()
        if not session:
            return Response(
                {'message': 'No active session.'},
                status=status.HTTP_404_NOT_FOUND
            )

        check = AvailabilityCheck.objects.filter(
            attendance_session=session, status='pending'
        ).order_by('-created_at').first()

        if not check:
            return Response(
                {'message': 'No pending check.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if check.auto_miss_if_expired():
            return Response(
                {'message': 'Check expired.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(AvailabilityCheckSerializer(check).data)


# INTERN — respond to their pending check

class RespondAvailabilityView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, IsIntern]

    def post(self, request, *args, **kwargs):
        session = AttendanceSession.objects.filter(
            user=request.user, status='active'
        ).first()
        if not session:
            return Response(
                {'error': 'No active session.'},
                status=status.HTTP_404_NOT_FOUND
            )

        check = AvailabilityCheck.objects.filter(
            attendance_session=session, status='pending'
        ).order_by('-created_at').first()
        if not check:
            return Response(
                {'error': 'No pending availability check.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if check.is_expired:
            check.auto_miss_if_expired()
            return Response(
                {'error': 'The check has expired.'},
                status=status.HTTP_410_GONE
            )

        check.respond()

        for lead in User.objects.filter(
            role__in=['team_lead', 'admin'],
            is_active=True
        ):
            Notification.objects.create(
                recipient=lead,
                sender=request.user,
                notification_type='system',
                message=f'{request.user.username} is available.',
                related_object_id=check.id,
                related_object_type='AvailabilityCheck',
            )

        return Response({
            'message': 'Availability confirmed.',
            'check': AvailabilityCheckSerializer(check).data,
        })


# INTERN — mark their own check as missed (called from the popup timer)

class MarkMissedView(generics.GenericAPIView):
    """
    Intern's popup timer expired — mark the check missed now,
    so the DB doesn't keep it as pending.
    """
    permission_classes = [permissions.IsAuthenticated, IsIntern]

    def post(self, request, *args, **kwargs):
        check_id = request.data.get('check_id')
        if not check_id:
            return Response(
                {'error': 'check_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            check = AvailabilityCheck.objects.get(
                id=check_id,
                attendance_session__user=request.user,
                status='pending',
            )
        except AvailabilityCheck.DoesNotExist:
            return Response(
                {'error': 'Check not found or already resolved.'},
                status=status.HTTP_404_NOT_FOUND
            )

        check.auto_miss_if_expired()

        return Response({
            'message': 'Marked as missed.',
            'status': check.status,
        })


# INTERN — own history

class AvailabilityHistoryView(generics.ListAPIView):
    serializer_class = AvailabilityCheckSerializer
    permission_classes = [permissions.IsAuthenticated, IsIntern]

    def get_queryset(self):
        for check in AvailabilityCheck.objects.filter(
            attendance_session__user=self.request.user,
            status='pending',
        ):
            check.auto_miss_if_expired()

        return AvailabilityCheck.objects.filter(
            attendance_session__user=self.request.user
        ).order_by('-created_at')


# LEAD — all checks (with optional filters)

class AllAvailabilityChecksView(generics.ListAPIView):
    serializer_class = AvailabilityCheckSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def get_queryset(self):
        for check in AvailabilityCheck.objects.filter(status='pending'):
            check.auto_miss_if_expired()

        qs = AvailabilityCheck.objects.all().order_by('-created_at')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        user_id = self.request.query_params.get('user')
        if user_id:
            qs = qs.filter(attendance_session__user_id=user_id)

        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(created_at__date=date)

        return qs


# LEAD — today's missed checks

class MissedChecksView(generics.ListAPIView):
    serializer_class = AvailabilityCheckSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def get_queryset(self):
        for check in AvailabilityCheck.objects.filter(status='pending'):
            check.auto_miss_if_expired()

        today = timezone.now().date()
        return AvailabilityCheck.objects.filter(
            status='missed',
            created_at__date=today,
        ).order_by('-created_at')