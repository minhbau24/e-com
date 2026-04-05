from django.urls import path
from .views import ManagerListCreateAPIView

urlpatterns = [
    path("managers/", ManagerListCreateAPIView.as_view()),
]
