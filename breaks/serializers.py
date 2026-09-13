from rest_framework import serializers
from .models import Break


class BreakSerializer(serializers.ModelSerializer):
    duration = serializers.DurationField(read_only=True)
    break_type_display = serializers.CharField(
        source='get_break_type_display',
        read_only=True
    )
    
    class Meta:
        model = Break
        fields = (
            'id', 'attendance_session', 'break_type', 'break_type_display',
            'start_time', 'end_time', 'duration', 'status',
            'notes', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'start_time', 'end_time', 'duration',
            'status', 'created_at', 'updated_at'
        )


class StartBreakSerializer(serializers.Serializer):
    break_type = serializers.ChoiceField(
        choices=Break.BREAK_TYPE_CHOICES,
        required=True
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255
    )
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # 1. Check if user has an active attendance session
        try:
            session = user.attendance_sessions.get(status='active')
        except Exception:
            raise serializers.ValidationError(
                "You don't have an active attendance session. Please log in first."
            )
        
        # 2. Check if already on break
        if Break.objects.filter(attendance_session=session, status='active').exists():
            raise serializers.ValidationError(
                "You are already on a break. Please end the current break first."
            )
        
        self.context['session'] = session
        return attrs


class EndBreakSerializer(serializers.Serializer):
    """Empty serializer for ending a break."""
    pass