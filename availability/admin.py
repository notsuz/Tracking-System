from django.contrib import admin
from .models import AvailabilityCheck

@admin.register(AvailabilityCheck)
class AvailabilityCheckAdmin(admin.ModelAdmin):
    list_display = ('attendance_session', 'created_at', 'status', 'notified_lead')
    list_filter = ('status', 'notified_lead', 'created_at')
    search_fields = ('attendance_session__user__email',)
    readonly_fields = ('created_at', 'responded_at')
