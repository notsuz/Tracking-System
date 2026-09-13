from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from core.views import (
    LoginRequiredTemplateView,
    SuperAdminRequiredTemplateView,
    CustomLoginView,
    CustomLogoutView,
    RoleBasedHomeView,
    session_login,
    AdminPanelTasksView,
    AdminPanelInternsView,
    AdminPanelAttendanceView,
    AdminPanelTeamLeadsView,
)

schema_view = get_schema_view(
    openapi.Info(
        title="Internship Management System API",
        default_version='v1',
        description="API for managing internships",
        contact=openapi.Contact(email="contact@internship.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Swagger
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # API routes
    path('api/accounts/', include('accounts.urls')),
    path('api/attendance/', include('attendance.urls')),
    path('api/breaks/', include('breaks.urls')),
    path('api/availability/', include('availability.urls')),
    path('api/tasks/', include('tasks.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/', include('core.urls')),

    # ===== Auth =====
    path('', RoleBasedHomeView.as_view(), name='home'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('change-password/',
         LoginRequiredTemplateView.as_view(template_name='accounts/change_password.html'),
         name='change_password'),

    # ===== Intern =====
    path('dashboard/', LoginRequiredTemplateView.as_view(template_name='intern/dashboard.html'), name='dashboard'),
    path('attendance/', LoginRequiredTemplateView.as_view(template_name='intern/attendance.html'), name='attendance'),
    path('breaks/', LoginRequiredTemplateView.as_view(template_name='intern/breaks.html'), name='breaks'),
    path('my-tasks/', LoginRequiredTemplateView.as_view(template_name='intern/tasks.html'), name='my_tasks'),
    path('daily-report/', LoginRequiredTemplateView.as_view(template_name='intern/daily_report.html'), name='daily_report'),

    # ===== Team Lead =====
    path('lead/dashboard/', LoginRequiredTemplateView.as_view(template_name='lead/dashboard.html'), name='lead_dashboard'),
    path('lead/interns/', LoginRequiredTemplateView.as_view(template_name='lead/interns.html'), name='interns'),
    path('lead/attendance/', LoginRequiredTemplateView.as_view(template_name='lead/attendance.html'), name='lead_attendance'),
    path('lead/tasks/', LoginRequiredTemplateView.as_view(template_name='lead/tasks.html'), name='lead_tasks'),
    path('lead/assign-task/', LoginRequiredTemplateView.as_view(template_name='lead/assign_task.html'), name='assign_task'),
    path('lead/reports/', LoginRequiredTemplateView.as_view(template_name='lead/reports.html'), name='lead_reports'),

    # ===== Super Admin =====
    path('admin-panel/',
         SuperAdminRequiredTemplateView.as_view(template_name='admin_panel/dashboard.html'),
         name='admin_panel_dashboard'),
    path('admin-panel/users/',
         SuperAdminRequiredTemplateView.as_view(template_name='admin_panel/users.html'),
         name='admin_panel_users'),
    path('admin-panel/users/create/',
         SuperAdminRequiredTemplateView.as_view(template_name='admin_panel/create_user.html'),
         name='admin_panel_create_user'),
    path('admin-panel/team-leads/',
         AdminPanelTeamLeadsView.as_view(),
         name='admin_panel_team_leads'),
    path('admin-panel/interns/',
         AdminPanelInternsView.as_view(),
         name='admin_panel_interns'),
    path('admin-panel/attendance/',
         AdminPanelAttendanceView.as_view(),
         name='admin_panel_attendance'),
    path('admin-panel/tasks/',
         AdminPanelTasksView.as_view(),
         name='admin_panel_tasks'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)