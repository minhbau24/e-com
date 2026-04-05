from django.db import models


class Shipment(models.Model):
    order_id = models.IntegerField()
    customer_id = models.IntegerField()
    address = models.CharField(max_length=255)
    status = models.CharField(max_length=30, default="CREATED")
    tracking_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
