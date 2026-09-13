from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView, LogoutView, ProfileView, ChangePasswordView,
    AdminUserListView, AdminCreateUserView, AdminUserDetailView,
    AdminResetUserPasswordView, AdminOverviewView,
    AdminTeamLeadsView, AdminAllTasksView,
)

urlpatterns = [
    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Super Admin — analytics
    path('admin/overview/', AdminOverviewView.as_view(), name='admin-overview'),
    path('admin/team-leads/', AdminTeamLeadsView.as_view(), name='admin-team-leads'),
    path('admin/all-tasks/', AdminAllTasksView.as_view(), name='admin-all-tasks'),

    # Super Admin — user management
    path('admin/users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('admin/users/create/', AdminCreateUserView.as_view(), name='admin-user-create'),
    path('admin/users/<int:pk>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    path('admin/users/<int:pk>/reset-password/', AdminResetUserPasswordView.as_view(), name='admin-user-reset-password'),
]