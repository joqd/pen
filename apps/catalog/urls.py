from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, CollectionViewSet, ProductViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'collections', CollectionViewSet, basename='collection')
router.register(r'categories', CategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
]
