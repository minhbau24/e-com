"""URL configuration for search_project."""

from django.urls import include, path

urlpatterns = [
    path("", include("search.urls")),
]
