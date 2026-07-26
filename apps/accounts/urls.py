from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.addresses_view import (
    AddressViewSet,
    CityListAPIView,
    ProvinceCityListAPIView,
    ProvinceListAPIView,
)
from .views.login_view import LoginAPIView, VerifyOTPAPIView
from .views.logout_view import LogoutAPIView
from .views.me_view import MeAPIView

router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='addresses')


urlpatterns = [
    path('login/', LoginAPIView.as_view()),
    path('verify/', VerifyOTPAPIView.as_view()),
    path('logout/', LogoutAPIView.as_view()),
    path('me/', MeAPIView.as_view()),
    path('', include(router.urls)),
    path('provinces/', ProvinceListAPIView.as_view()),
    path('provinces/<int:province_id>/cities/', ProvinceCityListAPIView.as_view()),
    path('cities/', CityListAPIView.as_view()),
]
