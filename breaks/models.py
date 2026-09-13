from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Break(models.Model):
    BREAK_TYPE_CHOICES = (
        ('lunch', 'Lunch Break'),
        ('restroom', 'Restroom'),
        ('training', 'Training'),
        ('meeting', 'Meeting'),
        ('personal', 'Personal'),
        ('other', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    attendance_session = models.ForeignKey(
        'attendance.AttendanceSession',
        on_delete=models.CASCADE,
        related_name='breaks'
    )
    break_type = models.CharField(
        max_length=20,
        choices=BREAK_TYPE_CHOICES,
        default='other'
    )
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'breaks'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['attendance_session', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_break_type_display()} - {self.attendance_session.user.email}"
    
    def end_break(self):
        self.end_time = timezone.now()
        self.duration = self.end_time - self.start_time
        self.status = 'completed'
        self.save()
        return self
    
    def cancel_break(self):
        self.status = 'cancelled'
        self.save()
        return self