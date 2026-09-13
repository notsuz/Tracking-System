from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'assigned_to', 'assigned_by', 'priority', 'status', 'deadline')
    list_filter = ('priority', 'status', 'created_at')
    search_fields = ('title', 'description', 'assigned_to__email')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
