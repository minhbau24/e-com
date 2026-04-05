from rest_framework import serializers
from .models import GatewayRequestLog


class GatewayRequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GatewayRequestLog
        fields = "__all__"
