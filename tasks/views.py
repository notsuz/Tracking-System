from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import Task
from .serializers import (
    TaskSerializer,
    TaskUpdateSerializer,
    TaskStatusUpdateSerializer,
)
from accounts.permissions import IsIntern, IsTeamLeadOrAdmin


class TaskListView(generics.ListAPIView):
    """List tasks (filtered by role)."""
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'priority']

    def get_queryset(self):
        user = self.request.user

        if user.role in ['team_lead', 'admin'] or user.is_superuser:
            queryset = Task.objects.all()
            assigned_to = self.request.query_params.get('assigned_to')
            if assigned_to:
                queryset = queryset.filter(assigned_to_id=assigned_to)
        else:
            queryset = Task.objects.filter(assigned_to=user)

        overdue = self.request.query_params.get('overdue')
        if overdue and overdue.lower() == 'true':
            queryset = queryset.filter(
                deadline__lte=timezone.now(),
                status__in=['assigned', 'in_progress'],
            )

        return queryset.order_by('-created_at')


class TaskCreateView(generics.CreateAPIView):
    """Create task (Team Lead / Admin only)."""
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsTeamLeadOrAdmin]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role in ['team_lead', 'admin'] or user.is_superuser:
            return Task.objects.all()
        return Task.objects.filter(assigned_to=user)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            if self.request.user.role in ['team_lead', 'admin'] or self.request.user.is_superuser:
                return TaskUpdateSerializer
        return TaskSerializer


class TaskStatusUpdateView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskStatusUpdateSerializer

    def get_object(self):
        task_id = self.kwargs.get('pk')
        user = self.request.user
        if user.role in ['team_lead', 'admin'] or user.is_superuser:
            return Task.objects.get(id=task_id)
        return Task.objects.get(id=task_id, assigned_to=user)

    def patch(self, request, *args, **kwargs):
        task = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        status_value = serializer.validated_data['status']
        if status_value == 'completed':
            task.complete()
        elif status_value == 'in_progress':
            task.start_progress()
        elif status_value == 'cancelled':
            task.cancel()
        else:
            task.status = status_value
            task.save()

        return Response(TaskSerializer(task).data)


class MyTasksView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsIntern]

    def get_queryset(self):
        return Task.objects.filter(assigned_to=self.request.user).order_by('-created_at')