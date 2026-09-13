from django.db import models
from django.conf import settings
from django.utils import timezone


class AvailabilityCheck(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('responded', 'Responded'),
        ('missed', 'Missed'),
    )

    attendance_session = models.ForeignKey(
        'attendance.AttendanceSession',
        on_delete=models.CASCADE,
        related_name='availability_checks'
    )
    created_at = models.DateTimeField(default=timezone.now)
    responded_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notified_lead = models.BooleanField(default=False)

    class Meta:
        db_table = 'availability_checks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['attendance_session', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return (
            f"AvailabilityCheck #{self.pk} ({self.status}) - "
            f"{self.attendance_session.user.username}"
        )

    # Core actions

    def respond(self):
        """Mark this check as responded."""
        self.responded_at = timezone.now()
        self.status = 'responded'
        self.save(update_fields=['responded_at', 'status'])
        return self

    def mark_missed(self, notify=True):
        """
        Mark this check as missed.
        If notify=True, sends a notification to all team leads/admins.
        """
        self.status = 'missed'
        self.notified_lead = True
        self.save(update_fields=['status', 'notified_lead'])

        if notify:
            try:
                self._notify_leads_missed()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(
                    f"Failed to notify leads for check #{self.pk}: {e}"
                )

        return self

    # Status helpers

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def is_responded(self):
        return self.status == 'responded'

    @property
    def is_missed(self):
        return self.status == 'missed'

    @property
    def timeout_seconds(self):
        """The configured timeout for this check."""
        return getattr(settings, 'AVAILABILITY_RESPONSE_TIMEOUT', 300)

    @property
    def seconds_elapsed(self):
        """
        Seconds since the check was created.

        Works with mixed naive/aware datetimes.
        When USE_TZ=False, both `timezone.now()` and `self.created_at`
        are naive — subtraction is safe. When USE_TZ=True, both are
        aware — subtraction is also safe. The only dangerous case is
        a mix; we normalize by stripping tzinfo from both sides.
        """
        if not self.created_at:
            return 0

        now = timezone.now()
        created = self.created_at

        # If one has tzinfo and the other doesn't, strip both
        if (now.tzinfo is None) != (created.tzinfo is None):
            now = now.replace(tzinfo=None)
            created = created.replace(tzinfo=None)

        return (now - created).total_seconds()

    @property
    def seconds_remaining(self):
        """Seconds until this check expires (0 if already past)."""
        if self.status != 'pending':
            return 0
        return max(0, self.timeout_seconds - self.seconds_elapsed)

    @property
    def is_expired(self):
        """True if this check is still pending but its deadline has passed."""
        if self.status != 'pending':
            return False
        return self.seconds_elapsed > self.timeout_seconds

    # Lazy auto-miss (no background process needed)

    def auto_miss_if_expired(self):
        """
        If this check is still pending but past its deadline,
        mark it missed and notify leads.

        Call this anywhere you read a check — the moment someone
        looks at a stale pending check, it gets resolved.

        Returns:
            True if the check was just marked missed.
            False if it wasn't expired or is no longer pending.
        """
        if not self.is_expired:
            return False

        self.mark_missed(notify=True)
        return True

    # Notifications

    def _notify_leads_missed(self):
        """Send a notification to every team lead and admin."""
        from notifications.models import Notification
        from django.contrib.auth import get_user_model
        User = get_user_model()

        intern = self.attendance_session.user
        for lead in User.objects.filter(
            role__in=['team_lead', 'admin'],
            is_active=True
        ):
            Notification.objects.create(
                recipient=lead,
                sender=intern,
                notification_type='availability_missed',
                message=(
                    f'{intern.username} did not respond to the '
                    f'availability check.'
                ),
                related_object_id=self.id,
                related_object_type='AvailabilityCheck',
            )