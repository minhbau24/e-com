"""URL patterns for the search app."""

from django.urls import path

from core.views import HealthView, SearchView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("search", SearchView.as_view(), name="search"),
]
