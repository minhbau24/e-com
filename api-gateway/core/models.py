from django.db import models


class GatewayRequestLog(models.Model):
    service = models.CharField(max_length=80)
    path = models.CharField(max_length=255)
    status_code = models.IntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True)
