from django.urls import path
from .views import ProductReviewListCreateAPIView, ProductReviewStatsAPIView, ReviewListCreateAPIView

urlpatterns = [
    path("reviews/", ReviewListCreateAPIView.as_view()),
    path("products/<int:product_id>/reviews/", ProductReviewListCreateAPIView.as_view()),
    path("products/<int:product_id>/reviews/stats/", ProductReviewStatsAPIView.as_view()),
]
