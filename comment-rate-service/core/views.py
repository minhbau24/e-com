from django.db.models import Avg, Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Review
from .serializers import ReviewSerializer


class ReviewListCreateAPIView(APIView):
    def get(self, request):
        book_id = request.query_params.get("book_id")
        queryset = Review.objects.all().order_by("-id")
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        return Response(ReviewSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductReviewListCreateAPIView(APIView):
    def get(self, request, product_id):
        sort = request.query_params.get("sort", "newest")
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 5))

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 50:
            page_size = 5

        queryset = Review.objects.filter(product_id=product_id)

        if sort == "highest":
            queryset = queryset.order_by("-rating", "-created_at")
        elif sort == "lowest":
            queryset = queryset.order_by("rating", "-created_at")
        else:
            queryset = queryset.order_by("-created_at")

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_items = queryset[start:end]

        return Response(
            {
                "results": ReviewSerializer(page_items, many=True).data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "has_next": end < total,
                },
            }
        )

    def post(self, request, product_id):
        payload = dict(request.data)
        payload["product_id"] = product_id
        payload.setdefault("book_id", product_id)
        serializer = ReviewSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProductReviewStatsAPIView(APIView):
    def get(self, request, product_id):
        queryset = Review.objects.filter(product_id=product_id)
        total = queryset.count()
        average = queryset.aggregate(avg=Avg("rating")).get("avg") or 0
        grouped = queryset.values("rating").annotate(count=Count("id"))

        count_map = {item["rating"]: item["count"] for item in grouped}
        breakdown = {}
        for star in range(5, 0, -1):
            count = count_map.get(star, 0)
            percentage = round((count / total) * 100, 1) if total else 0
            breakdown[str(star)] = {
                "count": count,
                "percentage": percentage,
            }

        return Response(
            {
                "product_id": product_id,
                "average_rating": round(float(average), 2),
                "total_reviews": total,
                "breakdown": breakdown,
            }
        )
