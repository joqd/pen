from django.urls import path

from .views.login_views import LoginAPIView, VerifyOTPAPIView
from .views.logout_views import LogoutAPIView
from .views.me_views import MeAPIView


urlpatterns = [
	path('login/', LoginAPIView.as_view()),
	path('verify/', VerifyOTPAPIView.as_view()),
	path('logout/', LogoutAPIView.as_view()),
	path('me/', MeAPIView.as_view()),
]