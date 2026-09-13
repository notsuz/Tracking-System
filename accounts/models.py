from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Super Admin'),
        ('team_lead', 'Team Lead'),
        ('intern', 'Intern'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='intern')
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    date_of_joining = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(
        default=True,
        help_text="If True, user must change password on next login."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.get_full_name() or self.email})"

    def save(self, *args, **kwargs):
        # Superusers / staff are always admins
        if self.is_superuser or self.is_staff:
            self.role = 'admin'
        super().save(*args, **kwargs)

    @property
    def is_intern(self):
        return self.role == 'intern'

    @property
    def is_team_lead(self):
        return self.role == 'team_lead'

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def display_name(self):
        full = self.get_full_name()
        return full if full.strip() else self.username

    @property
    def initials(self):
        first = (self.first_name or '').strip()
        last = (self.last_name or '').strip()

        if first and last:
            return f"{first[0]}{last[0]}".upper()
        if first:
            return first[0].upper()
        if last:
            return last[0].upper()
        if self.username:
            return self.username[0].upper()
        return '?'