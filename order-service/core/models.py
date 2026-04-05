from django.db import models


class Order(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("PARTIAL", "Partial"),
        ("FAILED", "Failed"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
    ]
    SHIPMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CREATED", "Created"),
        ("FAILED", "Failed"),
    ]

    customer_id = models.IntegerField()
    cart_id = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")
    payment_status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default="PENDING")
    shipment_status = models.CharField(max_length=30, choices=SHIPMENT_STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    book_id = models.IntegerField()
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
