from django.contrib import admin
from .models import AttendanceSession

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'logout_time', 'status', 'date')
    list_filter = ('status', 'date')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-login_time',)
