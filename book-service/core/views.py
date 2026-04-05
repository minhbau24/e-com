from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Book
from .serializers import BookSerializer


class BookListCreateAPIView(APIView):
    def get(self, request):
        return Response(BookSerializer(Book.objects.all().order_by("-id"), many=True).data)

    def post(self, request):
        serializer = BookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookDetailAPIView(APIView):
    def get_object(self, pk):
        return Book.objects.filter(pk=pk).first()

    def get(self, request, pk):
        book = self.get_object(pk)
        if not book:
            return Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BookSerializer(book).data)

    def put(self, request, pk):
        book = self.get_object(pk)
        if not book:
            return Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BookSerializer(book, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        book = self.get_object(pk)
        if not book:
            return Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)
        book.delete()
        return Response({"detail": "Book deleted."})


class BookValidateAPIView(APIView):
    def get(self, request, pk):
        book = Book.objects.filter(pk=pk).first()
        if not book:
            return Response({"valid": False, "reason": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"valid": True, "book_id": book.id, "stock": book.stock, "price": str(book.price)})
