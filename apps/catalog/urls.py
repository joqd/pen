from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProductViewSet, CollectionViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'collections', CollectionViewSet, basename='collection')

urlpatterns = [
    path('', include(router.urls)),
]
