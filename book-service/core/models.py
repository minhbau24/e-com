from django.db import models


class Book(models.Model):
    external_id = models.BigIntegerField(unique=True, null=True, blank=True)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=120, blank=True, default="")
    isbn = models.CharField(max_length=40, blank=True, default="")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    short_description = models.TextField(blank=True, default="")
    description = models.TextField(blank=True)
    rating_average = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    review_count = models.IntegerField(default=0)
    quantity_sold = models.IntegerField(default=0)
    image_base_url = models.TextField(blank=True, default="")
    image_large_url = models.TextField(blank=True, default="")
    image_medium_url = models.TextField(blank=True, default="")
    image_small_url = models.TextField(blank=True, default="")
    image_thumbnail_url = models.TextField(blank=True, default="")
    source_category = models.CharField(max_length=80, blank=True, default="uncategorized")
    source_brand = models.CharField(max_length=80, blank=True, default="unknown")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["source_category"]),
        ]

    def __str__(self):
        return f"{self.id} - {self.title}"
