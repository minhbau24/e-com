from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(required=False)

    class Meta:
        model = Review
        fields = "__all__"

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("rating must be between 1 and 5")
        return value

    def validate(self, attrs):
        product_id = attrs.get("product_id")
        book_id = attrs.get("book_id")
        if product_id is None and book_id is None:
            raise serializers.ValidationError("product_id is required")
        return attrs

    def create(self, validated_data):
        product_id = validated_data.get("product_id")
        if product_id is None:
            product_id = validated_data.get("book_id")
            validated_data["product_id"] = product_id
        validated_data.setdefault("book_id", product_id)
        return super().create(validated_data)
