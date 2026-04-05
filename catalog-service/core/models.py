from django.db import models


class CatalogEntry(models.Model):
    book_id = models.IntegerField()
    category = models.CharField(max_length=80)
    tags = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
