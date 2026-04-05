import os
import requests
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import CatalogEntry
from .serializers import CatalogEntrySerializer

BOOK_SERVICE_URL = os.getenv("BOOK_SERVICE_URL", "http://book-service:8000")


class CatalogListCreateAPIView(APIView):
    def get(self, request):
        category = request.query_params.get("category")
        queryset = CatalogEntry.objects.all()
        if category:
            queryset = queryset.filter(category=category)
        return Response(CatalogEntrySerializer(queryset, many=True).data)

    def post(self, request):
        serializer = CatalogEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CatalogBrowseAPIView(APIView):
    def get(self, request):
        category = request.query_params.get("category")
        entries = CatalogEntry.objects.filter(is_active=True)
        if category:
            entries = entries.filter(category=category)

        books = requests.get(f"{BOOK_SERVICE_URL}/books/", timeout=4).json()
        by_id = {item["id"]: item for item in books}

        result = []
        for entry in entries:
            book = by_id.get(entry.book_id)
            if book:
                result.append(
                    {
                        "catalog_id": entry.id,
                        "category": entry.category,
                        "tags": entry.tags,
                        "book": book,
                    }
                )
        return Response(result)
