from django.urls import path
from .views import CustomerDetailAPIView, CustomerListCreateAPIView, LoginAPIView, RegisterAPIView

urlpatterns = [
    path("customers/", CustomerListCreateAPIView.as_view()),
    path("customers/<int:pk>/", CustomerDetailAPIView.as_view()),
    path("auth/register/", RegisterAPIView.as_view()),
    path("auth/login/", LoginAPIView.as_view()),
]
