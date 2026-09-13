from django.urls import path
from .views import (
    StartBreakView, EndBreakView, CurrentBreakView,
    BreakHistoryView, AllBreaksView,
)

urlpatterns = [
    path('start/', StartBreakView.as_view(), name='start-break'),
    path('end/', EndBreakView.as_view(), name='end-break'),
    path('current/', CurrentBreakView.as_view(), name='current-break'),
    path('history/', BreakHistoryView.as_view(), name='break-history'),
    path('all/', AllBreaksView.as_view(), name='all-breaks'),
]