from django.urls import path

from .views.cart_view import (
    CartItemCreateView,
    CartItemView,
    CartView,
)

from .views.wishlist_view import (
    WishlistItemCreateView,
    WishlistItemView,
    WishlistView,
)

from .views.payment_view import (
	OrderCreateAPIView,
	OrderDetailAPIView,
	ActiveGatewayListAPIView,
	PaymentCallbackAPIView,
	PaymentCreateAPIView
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/', CartItemCreateView.as_view(), name='cart-add-item'),
    path('cart/items/<str:sku>/', CartItemView.as_view(), name='cart-item'),
    
	path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/items/', WishlistItemCreateView.as_view(), name='wishlist-add-item'),
    path('wishlist/items/<slug:slug>/', WishlistItemView.as_view(), name='wishlist-item'),

	path('checkout/orders/', OrderCreateAPIView.as_view(), name='order-create'),
    path('orders/<uuid:token>/', OrderDetailAPIView.as_view(), name='order-detail'),
    path('checkout/gateways/', ActiveGatewayListAPIView.as_view(), name='gateway-list'),
    path('checkout/orders/<uuid:token>/pay/', PaymentCreateAPIView.as_view(), name='payment-create'),
    path('payments/callback/<str:gateway_origin>/', PaymentCallbackAPIView.as_view(), name='payment-callback'),
]
