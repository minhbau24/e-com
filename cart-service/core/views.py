import os
import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Cart, CartItem
from .serializers import CartItemSerializer, CartSerializer

BOOK_SERVICE_URL = os.getenv("BOOK_SERVICE_URL", "http://book-service:8000")


class CartListCreateAPIView(APIView):
    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        queryset = Cart.objects.all()
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return Response(CartSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart, _ = Cart.objects.get_or_create(customer_id=serializer.validated_data["customer_id"])
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


class CartDetailAPIView(APIView):
    def get(self, request, pk):
        cart = Cart.objects.filter(pk=pk).first()
        if not cart:
            return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)
        data = CartSerializer(cart).data
        data["items"] = CartItemSerializer(cart.items.all(), many=True).data
        return Response(data)


class CartItemListCreateAPIView(APIView):
    def get(self, request):
        cart_id = request.query_params.get("cart_id")
        queryset = CartItem.objects.all()
        if cart_id:
            queryset = queryset.filter(cart_id=cart_id)
        return Response(CartItemSerializer(queryset, many=True).data)

    def post(self, request):
        cart_id = request.data.get("cart")
        book_id = request.data.get("book_id")

        cart = Cart.objects.filter(pk=cart_id).first()
        if not cart:
            return Response({"detail": "Cart not found."}, status=status.HTTP_404_NOT_FOUND)

        validate = requests.get(f"{BOOK_SERVICE_URL}/books/{book_id}/validate/", timeout=4)
        if validate.status_code >= 400:
            return Response({"detail": "Invalid book."}, status=status.HTTP_400_BAD_REQUEST)

        book_data = requests.get(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=4).json()
        payload = dict(request.data)
        payload["unit_price"] = book_data.get("price", 0)

        serializer = CartItemSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CartItemDetailAPIView(APIView):
    def put(self, request, pk):
        item = CartItem.objects.filter(pk=pk).first()
        if not item:
            return Response({"detail": "Cart item not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CartItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
