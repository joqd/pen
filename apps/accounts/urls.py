from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.login_views import LoginAPIView, VerifyOTPAPIView
from .views.logout_views import LogoutAPIView
from .views.me_views import MeAPIView
from .views.addresses_views import (
	AddressViewSet,
	ProvinceListAPIView,
	ProvinceCityListAPIView,
	CityListAPIView,
)

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