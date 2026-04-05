import logging
import os
import time
import requests
from django.core import signing
from django.contrib.auth.hashers import make_password, check_password
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Customer
from .serializers import CustomerSerializer, LoginSerializer, RegisterSerializer

logger = logging.getLogger(__name__)
CART_SERVICE_URL = os.getenv("CART_SERVICE_URL", "http://cart-service:8000")


def post_with_retry(url, payload, retries=3, delay=1):
    last_error = None
    for _ in range(retries):
        try:
            return requests.post(url, json=payload, timeout=4)
        except requests.RequestException as exc:
            last_error = str(exc)
            time.sleep(delay)
    raise requests.RequestException(last_error)


class CustomerListCreateAPIView(APIView):
    def get(self, request):
        customers = Customer.objects.all().order_by("-id")
        return Response(CustomerSerializer(customers, many=True).data)

    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()

        try:
            cart_response = post_with_retry(
                f"{CART_SERVICE_URL}/carts/",
                {"customer_id": customer.id},
            )
            if cart_response.status_code >= 400:
                logger.warning("Cart creation failed for customer %s", customer.id)
                return Response(
                    {
                        "customer": CustomerSerializer(customer).data,
                        "warning": "Customer created, but cart creation failed.",
                    },
                    status=status.HTTP_201_CREATED,
                )
        except requests.RequestException as exc:
            logger.error("Cart service unavailable: %s", exc)
            return Response(
                {
                    "customer": CustomerSerializer(customer).data,
                    "warning": "Customer created, but cart service unavailable.",
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)


class CustomerDetailAPIView(APIView):
    def get_object(self, pk):
        return Customer.objects.filter(pk=pk).first()

    def get(self, request, pk):
        customer = self.get_object(pk)
        if not customer:
            return Response({"detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CustomerSerializer(customer).data)


class RegisterAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        if Customer.objects.filter(email=email).exists():
            return Response({"detail": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)

        customer = Customer.objects.create(
            name=serializer.validated_data["name"],
            email=email,
            address=serializer.validated_data.get("address", ""),
            password_hash=make_password(serializer.validated_data["password"]),
        )

        try:
            post_with_retry(
                f"{CART_SERVICE_URL}/carts/",
                {"customer_id": customer.id},
            )
        except requests.RequestException:
            logger.warning("Cart creation skipped for customer %s", customer.id)

        token = signing.dumps({"customer_id": customer.id, "email": customer.email}, salt="customer-auth")
        return Response(
            {
                "token": token,
                "customer": CustomerSerializer(customer).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].strip().lower()
        password = serializer.validated_data["password"]
        customer = Customer.objects.filter(email=email).first()

        if not customer or not customer.password_hash or not check_password(password, customer.password_hash):
            return Response({"detail": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        token = signing.dumps({"customer_id": customer.id, "email": customer.email}, salt="customer-auth")
        return Response(
            {
                "token": token,
                "customer": CustomerSerializer(customer).data,
            },
            status=status.HTTP_200_OK,
        )
