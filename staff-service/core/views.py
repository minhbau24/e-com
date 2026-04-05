import os
import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Staff
from .serializers import StaffSerializer

BOOK_SERVICE_URL = os.getenv("BOOK_SERVICE_URL", "http://book-service:8000")


class StaffListCreateAPIView(APIView):
    def get(self, request):
        return Response(StaffSerializer(Staff.objects.all(), many=True).data)

    def post(self, request):
        serializer = StaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StaffBookProxyAPIView(APIView):
    def get(self, request):
        response = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=4)
        return Response(response.json(), status=response.status_code)

    def post(self, request):
        response = requests.post(f"{BOOK_SERVICE_URL}/books/", json=request.data, timeout=4)
        return Response(response.json(), status=response.status_code)

    def put(self, request, book_id):
        response = requests.put(f"{BOOK_SERVICE_URL}/books/{book_id}/", json=request.data, timeout=4)
        return Response(response.json(), status=response.status_code)

    def delete(self, request, book_id):
        response = requests.delete(f"{BOOK_SERVICE_URL}/books/{book_id}/", timeout=4)
        data = response.json() if response.content else {"detail": "Deleted"}
        return Response(data, status=response.status_code)
