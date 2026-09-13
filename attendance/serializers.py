from rest_framework import serializers
from .models import AttendanceSession
from breaks.models import Break


class BreakSerializer(serializers.ModelSerializer):
    class Meta:
        model = Break
        fields = ('id', 'start_time', 'end_time', 'duration', 'status')
        read_only_fields = ('duration',)


class AttendanceSessionSerializer(serializers.ModelSerializer):
    breaks = BreakSerializer(many=True, read_only=True)
    duration = serializers.DurationField(read_only=True)
    total_break_time = serializers.DurationField(read_only=True)
    working_time = serializers.DurationField(read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = AttendanceSession
        fields = (
            'id', 'user', 'user_name', 'user_email', 
            'login_time', 'logout_time', 'status', 
            'logout_reason', 'daily_summary', 'date', 
            'duration', 'total_break_time', 'working_time', 
            'breaks', 'login_count', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'date', 'login_time', 'login_count', 
            'created_at', 'updated_at', 'duration', 
            'total_break_time', 'working_time'
        )


class EndAttendanceSerializer(serializers.Serializer):
    """Serializer for ending attendance session"""
    daily_summary = serializers.CharField(required=True, min_length=10)
    
    def validate_daily_summary(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Daily summary is required.")
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Please provide a meaningful summary (at least 10 characters)."
            )
        return value.strip()


class SessionStatusSerializer(serializers.Serializer):
    """Serializer for session status response"""
    has_session = serializers.BooleanField()
    is_new = serializers.BooleanField()
    message = serializers.CharField()
    session = AttendanceSessionSerializer(allow_null=True)


class LoginResponseSerializer(serializers.Serializer):
    """Serializer for login response with attendance info"""
    is_new = serializers.BooleanField()
    message = serializers.CharField()
    session = AttendanceSessionSerializer()