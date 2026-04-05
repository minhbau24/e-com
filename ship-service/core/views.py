from uuid import uuid4
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Shipment
from .serializers import ShipmentSerializer


class ShipmentListCreateAPIView(APIView):
    def get(self, request):
        return Response(ShipmentSerializer(Shipment.objects.all(), many=True).data)

    def post(self, request):
        payload = dict(request.data)
        payload.setdefault("tracking_code", str(uuid4())[:10])
        payload.setdefault("status", "CREATED")
        serializer = ShipmentSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
