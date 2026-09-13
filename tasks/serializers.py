from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Task

User = get_user_model()


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.username', read_only=True)
    assigned_by_email = serializers.EmailField(source='assigned_by.email', read_only=True)
    time_taken = serializers.DurationField(read_only=True)

    class Meta:
        model = Task
        fields = (
            'id',
            'assigned_to', 'assigned_to_name', 'assigned_to_email',
            'assigned_by', 'assigned_by_name', 'assigned_by_email',
            'title', 'description', 'priority', 'status',
            'created_at', 'updated_at', 'deadline', 'completed_at',
            'notes', 'is_overdue', 'time_taken',
        )
        read_only_fields = (
            'id',
            'assigned_by',        #server sets it from request.user
            'assigned_by_name',
            'assigned_by_email',
            'created_at',
            'updated_at',
            'completed_at',
            'time_taken',
            'is_overdue',
        )

    def create(self, validated_data):
        #set assigned_by from the logged-in user
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)


class TaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ('title', 'description', 'priority', 'status', 'deadline', 'notes')

    def update(self, instance, validated_data):
        if validated_data.get('status') == 'completed' and instance.status != 'completed':
            validated_data['completed_at'] = timezone.now()
        return super().update(instance, validated_data)


class TaskStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.STATUS_CHOICES)