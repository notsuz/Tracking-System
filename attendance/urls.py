from django.urls import path
from .views import (
    StartAttendanceView,
    EndAttendanceView,
    CurrentAttendanceView,
    AttendanceHistoryView,
    AllAttendanceView,
    DailyAttendanceSummaryView,
    ForceLogoutView,
)

urlpatterns = [
    path('start/', StartAttendanceView.as_view(), name='start-attendance'),
    path('end/', EndAttendanceView.as_view(), name='end-attendance'),
    path('current/', CurrentAttendanceView.as_view(), name='current-attendance'),
    path('history/', AttendanceHistoryView.as_view(), name='attendance-history'),
    path('all/', AllAttendanceView.as_view(), name='all-attendance'),
    path('daily-summary/', DailyAttendanceSummaryView.as_view(), name='daily-summary'),
    path('force-logout/<int:user_id>/', ForceLogoutView.as_view(), name='force-logout'),
]