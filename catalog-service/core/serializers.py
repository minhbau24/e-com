from rest_framework import serializers
from .models import CatalogEntry


class CatalogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogEntry
        fields = "__all__"
