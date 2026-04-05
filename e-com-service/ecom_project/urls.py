"""URL configuration for ecom_project."""

from django.urls import include, path

urlpatterns = [
    path("", include("api.urls")),
]
