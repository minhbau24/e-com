from django.db import models


class Review(models.Model):
    customer_id = models.IntegerField(null=True, blank=True)
    book_id = models.IntegerField(null=True, blank=True)
    product_id = models.IntegerField(null=True, blank=True)
    user_name = models.CharField(max_length=120, default="Anonymous")
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
