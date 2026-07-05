from django.urls import path

from .views.login import LoginAPIView, VerifyOTPAPIView
from .views.logout import LogoutAPIView
from .views.me import MeAPIView


urlpatterns = [
	path('login/', LoginAPIView.as_view()),
	path('verify/', VerifyOTPAPIView.as_view()),
	path('logout/', LogoutAPIView.as_view()),
	path('me/', MeAPIView.as_view()),
]