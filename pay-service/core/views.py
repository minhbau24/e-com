from uuid import uuid4
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Payment
from .serializers import PaymentSerializer


class PaymentListCreateAPIView(APIView):
    def get(self, request):
        return Response(PaymentSerializer(Payment.objects.all(), many=True).data)

    def post(self, request):
        payload = dict(request.data)
        payload.setdefault("transaction_ref", str(uuid4())[:12])
        payload.setdefault("status", "PAID")
        serializer = PaymentSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
