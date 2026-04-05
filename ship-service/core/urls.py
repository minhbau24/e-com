from django.urls import path
from .views import ShipmentListCreateAPIView

urlpatterns = [
    path("shipments/", ShipmentListCreateAPIView.as_view()),
]
