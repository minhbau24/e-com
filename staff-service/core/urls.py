from django.urls import path
from .views import StaffBookProxyAPIView, StaffListCreateAPIView

urlpatterns = [
    path("staff/", StaffListCreateAPIView.as_view()),
    path("staff/books/", StaffBookProxyAPIView.as_view()),
    path("staff/books/<int:book_id>/", StaffBookProxyAPIView.as_view()),
]
