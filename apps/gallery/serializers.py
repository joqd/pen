from rest_framework import serializers

from .models import CustomerGallery


class CustomerGallerySerializer(serializers.ModelSerializer):
	# product_title = serializers.CharField(source='product.title', read_only=True)

	class Meta:
		model = CustomerGallery
		fields = [
			'id', 'image', 'customer_name',
			'caption', 'score', 'created_at',
			# 'product_title',
		]