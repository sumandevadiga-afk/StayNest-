from django.urls import path

from .views import AnalyticsOperationsView, AnalyticsOverviewView


urlpatterns = [
    path("overview/", AnalyticsOverviewView.as_view(), name="analytics-overview"),
    path("operations/", AnalyticsOperationsView.as_view(), name="analytics-operations"),
]
