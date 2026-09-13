from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ('id', 'recipient', 'recipient_name', 'sender', 'sender_name',
                 'sender_email', 'notification_type', 'message', 'is_read',
                 'created_at', 'read_at', 'related_object_id', 'related_object_type',
                 'time_ago')
        read_only_fields = ('id', 'created_at', 'read_at')
    
    def get_time_ago(self, obj):
        """Calculate time ago for the notification"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at)

class MarkNotificationReadSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of notification IDs to mark as read. If empty, marks all as read."
    )