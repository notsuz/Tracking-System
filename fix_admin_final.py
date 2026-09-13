import os

# Fix tasks/admin.py
with open('tasks/admin.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'assigned_by', 'priority', 'status', 'deadline')
    list_filter = ('priority', 'status', 'created_at')
    search_fields = ('title', 'description', 'assigned_to__email')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
""")
print("✅ Fixed: tasks/admin.py")

# Fix breaks/admin.py
with open('breaks/admin.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from .models import Break

@admin.register(Break)
class BreakAdmin(admin.ModelAdmin):
    list_display = ('attendance_session', 'start_time', 'end_time', 'duration', 'status')
    list_filter = ('status',)
    search_fields = ('attendance_session__user__email',)
    readonly_fields = ('created_at', 'updated_at')
""")
print("✅ Fixed: breaks/admin.py")

# Fix attendance/admin.py
with open('attendance/admin.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from .models import AttendanceSession

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'logout_time', 'status', 'date')
    list_filter = ('status', 'date')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-login_time',)
""")
print("✅ Fixed: attendance/admin.py")

# Fix notifications/admin.py
with open('notifications/admin.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'message', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('recipient__email', 'message')
    readonly_fields = ('created_at', 'read_at')
""")
print("✅ Fixed: notifications/admin.py")

# Fix availability/admin.py
with open('availability/admin.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from .models import AvailabilityCheck

@admin.register(AvailabilityCheck)
class AvailabilityCheckAdmin(admin.ModelAdmin):
    list_display = ('attendance_session', 'created_at', 'status', 'notified_lead')
    list_filter = ('status', 'notified_lead', 'created_at')
    search_fields = ('attendance_session__user__email',)
    readonly_fields = ('created_at', 'responded_at')
""")
print("✅ Fixed: availability/admin.py")

# Fix accounts/admin.py
with open('accounts/admin.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'role', 'first_name', 'last_name', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('username', 'first_name', 'last_name', 'phone', 'date_of_joining')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role'),
        }),
    )

admin.site.register(User, CustomUserAdmin)
""")
print("✅ Fixed: accounts/admin.py")

# Fix reports/admin.py
with open('reports/admin.py', 'w', encoding='utf-8') as f:
    f.write("""from django.contrib import admin
# No models to register for reports app yet
""")
print("✅ Fixed: reports/admin.py")

print("\n✅ All admin files fixed successfully!")
print("\nNow run:")
print("python manage.py makemigrations")
print("python manage.py migrate")
print("python manage.py createsuperuser")
print("python manage.py runserver")