from django.db import models


class Manager(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    level = models.CharField(max_length=30, default="L1")
    created_at = models.DateTimeField(auto_now_add=True)
