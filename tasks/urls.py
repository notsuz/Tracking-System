from django.urls import path
from .views import (
    TaskListView,
    TaskCreateView,
    TaskDetailView,
    TaskStatusUpdateView,
    MyTasksView,
)

urlpatterns = [
    path('', TaskListView.as_view(), name='task-list'),
    path('my-tasks/', MyTasksView.as_view(), name='my-tasks'),
    path('create/', TaskCreateView.as_view(), name='task-create'),
    path('<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('<int:pk>/status/', TaskStatusUpdateView.as_view(), name='task-status-update'),
]