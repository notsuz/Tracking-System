from django.contrib import admin
from .models import Break

@admin.register(Break)
class BreakAdmin(admin.ModelAdmin):
    list_display = ('attendance_session', 'start_time', 'end_time', 'duration', 'status')
    list_filter = ('status',)
    search_fields = ('attendance_session__user__email',)
    readonly_fields = ('created_at', 'updated_at')
