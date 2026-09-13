from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class AttendanceSession(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('force_logged_out', 'Force Logged Out'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendance_sessions'
    )
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    logout_reason = models.CharField(max_length=255, null=True, blank=True)
    login_count = models.IntegerField(default=1)
    daily_summary = models.TextField(null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_sessions'
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.login_time.strftime('%Y-%m-%d %H:%M')}"

    # Computed durations

    @property
    def duration(self):
        if self.logout_time:
            end_time = self.logout_time
        else:
            end_time = timezone.now()
        return end_time - self.login_time

    @property
    def total_break_time(self):
        total_break = timedelta(0)
        for break_item in self.breaks.all():
            if break_item.end_time:
                total_break += break_item.duration
        return total_break

    @property
    def working_time(self):
        return self.duration - self.total_break_time

    @property
    def is_active(self):
        return self.status == 'active' and not self.logout_time

    # Actions

    def close_session(self, logout_reason=None, daily_summary=None):
        """End Duty — blocks any further sessions today."""
        self.logout_time = timezone.now()
        self.status = 'completed'
        if logout_reason:
            self.logout_reason = logout_reason
        if daily_summary:
            self.daily_summary = daily_summary
        self.save()
        return self

    def pause_session(self, reason='Logged out by user'):
        """Logout — pauses the day. A new session can start later."""
        self.logout_time = timezone.now()
        self.status = 'paused'
        self.logout_reason = reason
        self.save()
        return self

    def force_logout(self, reason="Force logged out by Team Lead"):
        """Lead kicks intern — pauses the day. A new session can start later."""
        self.logout_time = timezone.now()
        self.status = 'force_logged_out'
        self.logout_reason = reason
        self.save()
        return self

    # Login handling


    @classmethod
    def handle_intern_login(cls, user, allow_relogin=False):
        """
        - Active session exists → continue it.
        - Completed today → block (duty ended).
        - Paused or force_logged_out today → create a new session.
        - Otherwise → create a new session.
        """
        today = timezone.now().date()

        # 1. Continue active session
        existing = cls.objects.filter(
            user=user, date=today, status='active'
        ).first()
        if existing:
            existing.login_count += 1
            existing.save(update_fields=['login_count', 'updated_at'])
            return existing, False, f"Welcome back! Login #{existing.login_count} today."

        # 2. Completed today → block
        completed = cls.objects.filter(
            user=user, date=today, status='completed'
        ).first()
        if completed:
            return completed, False, "You have already ended your duty for today."

        # 3. Paused or force-logged-out → new session
        prior = cls.objects.filter(
            user=user, date=today, status__in=['paused', 'force_logged_out']
        ).exists()
        if prior:
            new_session = cls.objects.create(
                user=user,
                login_time=timezone.now(),
                status='active',
                login_count=1,
            )
            return new_session, True, "Session resumed."

        # 4. No session today → new session
        new_session = cls.objects.create(
            user=user,
            login_time=timezone.now(),
            status='active',
            login_count=1,
        )
        return new_session, True, "Session started! Your time is now being tracked."


    @classmethod
    def daily_totals(cls, user, day=None):
        """Aggregate durations across all sessions for a user on a given day."""
        if day is None:
            day = timezone.now().date()

        sessions = cls.objects.filter(user=user, date=day)

        total_duration = timedelta(0)
        completed_duration = timedelta(0)
        total_break = timedelta(0)
        session_count = sessions.count()

        for s in sessions:
            total_duration += s.duration
            total_break += s.total_break_time
            if s.status != 'active':
                completed_duration += s.duration

        return {
            'total_duration': total_duration,
            'completed_duration': completed_duration,
            'total_break': total_break,
            'working_time': total_duration - total_break,
            'session_count': session_count,
        }