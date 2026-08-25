from django.urls import path

from .views.site_view import FooterBadgeListView, PaymentGatewayListView


urlpatterns = [
    path('footer-badges/', FooterBadgeListView.as_view()),
	path('payment-gateways/', PaymentGatewayListView.as_view()),
]
