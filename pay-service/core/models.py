from django.db import models


class Payment(models.Model):
    order_id = models.IntegerField()
    customer_id = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, default="PAID")
    transaction_ref = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
