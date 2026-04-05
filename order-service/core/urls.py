from django.urls import path
from .views import OrderListCreateAPIView

urlpatterns = [
    path("orders/", OrderListCreateAPIView.as_view()),
]
