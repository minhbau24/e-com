from django.urls import path
from .views import CartDetailAPIView, CartItemDetailAPIView, CartItemListCreateAPIView, CartListCreateAPIView

urlpatterns = [
    path("carts/", CartListCreateAPIView.as_view()),
    path("carts/<int:pk>/", CartDetailAPIView.as_view()),
    path("cart-items/", CartItemListCreateAPIView.as_view()),
    path("cart-items/<int:pk>/", CartItemDetailAPIView.as_view()),
]
