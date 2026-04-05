from django.urls import path
from .views import BookDetailAPIView, BookListCreateAPIView, BookValidateAPIView

urlpatterns = [
    path("books/", BookListCreateAPIView.as_view()),
    path("books/<int:pk>/", BookDetailAPIView.as_view()),
    path("books/<int:pk>/validate/", BookValidateAPIView.as_view()),
]
