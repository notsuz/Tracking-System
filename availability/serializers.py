from rest_framework import serializers
from .models import AvailabilityCheck


class AvailabilityCheckSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='attendance_session.user.username', read_only=True)
    user_id = serializers.IntegerField(source='attendance_session.user.id', read_only=True)
    response_time_seconds = serializers.SerializerMethodField()

    class Meta:
        model = AvailabilityCheck
        fields = (
            'id', 'attendance_session', 'user_id', 'username',
            'created_at', 'responded_at', 'status',
            'notified_lead', 'response_time_seconds',
        )
        read_only_fields = ('id', 'created_at', 'status', 'notified_lead')

    def get_response_time_seconds(self, obj):
        if obj.responded_at and obj.created_at:
            return int((obj.responded_at - obj.created_at).total_seconds())
        return None


class SendAvailabilityCheckSerializer(serializers.Serializer):
    """Lead sends availability check(s) to one or more interns."""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        min_length=1,
    )


class RespondAvailabilitySerializer(serializers.Serializer):
    """Intern responds to the pending check."""
    pass