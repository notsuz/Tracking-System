from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer, MarkNotificationReadSerializer

class NotificationListView(generics.ListAPIView):
    """
    Get notifications for the current user
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            is_read_bool = is_read.lower() == 'true'
            queryset = queryset.filter(is_read=is_read_bool)
        
        # Filter by type
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        return queryset

class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update or delete a specific notification
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)
    
    def update(self, request, *args, **kwargs):
        notification = self.get_object()
        is_read = request.data.get('is_read')
        
        if is_read is not None:
            if is_read:
                notification.mark_as_read()
            else:
                notification.mark_as_unread()
        
        return Response(self.get_serializer(notification).data)

class MarkNotificationsReadView(generics.GenericAPIView):
    """
    Mark one or more notifications as read
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MarkNotificationReadSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        notification_ids = serializer.validated_data.get('notification_ids')
        
        if notification_ids:
            # Mark specific notifications as read
            notifications = Notification.objects.filter(
                recipient=request.user,
                id__in=notification_ids,
                is_read=False
            )
            count = notifications.count()
            for notification in notifications:
                notification.mark_as_read()
            message = f"{count} notifications marked as read."
        else:
            # Mark all notifications as read
            notifications = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            )
            count = notifications.count()
            for notification in notifications:
                notification.mark_as_read()
            message = f"All {count} notifications marked as read."
        
        return Response({
            'message': message,
            'count': count
        })

class UnreadNotificationCountView(generics.GenericAPIView):
    """
    Get count of unread notifications
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return Response({
            'unread_count': count
        })