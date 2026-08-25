from django.urls import path

from .views.cart_view import (
    CartItemCreateView,
    CartItemView,
    CartView,
)
from .views.checkout_view import CheckoutInitiateView, PaymentCallbackView
from .views.order_status_view import OrderStatusView
from .views.wishlist_view import (
    WishlistItemCreateView,
    WishlistItemView,
    WishlistView,
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/', CartItemCreateView.as_view(), name='cart-add-item'),
    path('cart/items/<str:sku>/', CartItemView.as_view(), name='cart-item'),
    path('wishlist/', WishlistView.as_view(), name='wishlist'),
    path('wishlist/items/', WishlistItemCreateView.as_view(), name='wishlist-add-item'),
    path('wishlist/items/<slug:slug>/', WishlistItemView.as_view(), name='wishlist-item'),
    path('checkout/', CheckoutInitiateView.as_view(), name='checkout-initiate'),
    path('checkout/callback/', PaymentCallbackView.as_view(), name='payment-callback'),
    path('orders/<str:order_number>/', OrderStatusView.as_view(), name='order-status'),
]
