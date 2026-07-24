from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomerGalleryViewSet

router = DefaultRouter()
router.register(r'customers', CustomerGalleryViewSet, basename='customers')

urlpatterns = [
    path('', include(router.urls)),
]
