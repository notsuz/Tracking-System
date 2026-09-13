from django.urls import path
from .views import DailyReportView, InternReportView, CurrentStatusView

urlpatterns = [
    path('daily/', DailyReportView.as_view(), name='daily-report'),
    path('intern/', InternReportView.as_view(), name='intern-report'),
    path('current-status/', CurrentStatusView.as_view(), name='current-status'),
]