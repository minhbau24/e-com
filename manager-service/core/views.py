from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Manager
from .serializers import ManagerSerializer


class ManagerListCreateAPIView(APIView):
    def get(self, request):
        return Response(ManagerSerializer(Manager.objects.all(), many=True).data)

    def post(self, request):
        serializer = ManagerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
