from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Break
from .serializers import (
    BreakSerializer,
    StartBreakSerializer,
    EndBreakSerializer,
)
from accounts.permissions import IsIntern


class StartBreakView(generics.GenericAPIView):
    """
    Start a break. Requires an active attendance session.
    """
    permission_classes = [permissions.IsAuthenticated, IsIntern]
    serializer_class = StartBreakSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        session = serializer.context['session']
        break_type = serializer.validated_data['break_type']
        notes = serializer.validated_data.get('notes', '')
        
        # Create the break
        break_obj = Break.objects.create(
            attendance_session=session,
            break_type=break_type,
            notes=notes,
            status='active'
        )
        
        return Response(
            {
                'message': f'{break_obj.get_break_type_display()} started.',
                'break': BreakSerializer(break_obj).data
            },
            status=status.HTTP_201_CREATED
        )


class EndBreakView(generics.GenericAPIView):
    """
    End the current active break.
    """
    permission_classes = [permissions.IsAuthenticated, IsIntern]
    serializer_class = EndBreakSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            break_obj = Break.objects.get(
                attendance_session__user=request.user,
                status='active'
            )
        except Break.DoesNotExist:
            return Response(
                {'error': 'No active break found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        break_obj.end_break()
        
        return Response({
            'message': f'{break_obj.get_break_type_display()} ended.',
            'break': BreakSerializer(break_obj).data
        })


class CurrentBreakView(generics.GenericAPIView):
    """
    Get the currently active break.
    """
    permission_classes = [permissions.IsAuthenticated, IsIntern]
    serializer_class = BreakSerializer
    
    def get(self, request, *args, **kwargs):
        try:
            break_obj = Break.objects.get(
                attendance_session__user=request.user,
                status='active'
            )
            return Response(BreakSerializer(break_obj).data)
        except Break.DoesNotExist:
            return Response(
                {'message': 'No active break'},
                status=status.HTTP_404_NOT_FOUND
            )


class BreakHistoryView(generics.ListAPIView):
    """
    Get break history for the current user.
    """
    serializer_class = BreakSerializer
    permission_classes = [permissions.IsAuthenticated, IsIntern]
    
    def get_queryset(self):
        return Break.objects.filter(
            attendance_session__user=self.request.user
        ).order_by('-start_time')


class AllBreaksView(generics.ListAPIView):
    """
    Get all breaks (Team Lead/Admin only).
    """
    serializer_class = BreakSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user_role = self.request.user.role
        if user_role not in ['team_lead', 'admin']:
            return Break.objects.none()
        
        queryset = Break.objects.all().order_by('-start_time')
        
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(start_time__date=date)
        
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(attendance_session__user_id=user_id)
        
        break_type = self.request.query_params.get('break_type')
        if break_type:
            queryset = queryset.filter(break_type=break_type)
        
        return queryset