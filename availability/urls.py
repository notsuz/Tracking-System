from django.urls import path
from .views import (
    SendAvailabilityCheckView,
    PendingAvailabilityView,
    RespondAvailabilityView,
    MarkMissedView,
    AvailabilityHistoryView,
    AllAvailabilityChecksView,
    MissedChecksView,
)

urlpatterns = [
    path('send/', SendAvailabilityCheckView.as_view(), name='send-availability'),
    path('pending/', PendingAvailabilityView.as_view(), name='pending-availability'),
    path('respond/', RespondAvailabilityView.as_view(), name='respond-availability'),
    path('miss/', MarkMissedView.as_view(), name='mark-missed'),
    path('history/', AvailabilityHistoryView.as_view(), name='availability-history'),
    path('all/', AllAvailabilityChecksView.as_view(), name='all-availability'),
    path('missed/', MissedChecksView.as_view(), name='missed-checks'),
]