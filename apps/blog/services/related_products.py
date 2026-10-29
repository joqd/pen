from apps.catalog.models.product_model import Product, ProductStatus

RELATED_PRODUCTS_LIMIT = 8


def get_related_products_queryset(collection_ids):
    if not collection_ids:
        return Product.objects.none()

    return (
        Product.objects.filter(
            collections__id__in=collection_ids,
            status=ProductStatus.ACTIVE,
            variants__stock__gt=0,
        )
        .distinct()
        .prefetch_related('images', 'variants', 'collections')
        .order_by('-featured', '-published_at', '-id')[:RELATED_PRODUCTS_LIMIT]
    )
