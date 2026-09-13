from django.urls import path
from .views import (
    NotificationListView, NotificationDetailView,
    MarkNotificationsReadView, UnreadNotificationCountView
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', UnreadNotificationCountView.as_view(), name='unread-count'),
    path('mark-read/', MarkNotificationsReadView.as_view(), name='mark-read'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
]