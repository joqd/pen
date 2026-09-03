from django.urls import path

from .views.cart_view import (
    CartItemCreateView,
    CartItemView,
    CartView,
)
from .views.payment_view import (
    ActiveGatewayListAPIView,
    OrderAddressUpdateAPIView,
    OrderCancelAPIView,
    OrderDetailAPIView,
    OrderItemCreateAPIView,
    OrderItemUpdateDeleteAPIView,
    OrderListCreateAPIView,
    PaymentCallbackAPIView,
    PaymentCreateAPIView,
)
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
    # Orders: every order is addressed by its own public UUID `token`, not
    # by a cookie-resolved "current order" - a user can have many orders
    # (order history), and this exposes the full CRUD-ish surface for them.
    path('orders/', OrderListCreateAPIView.as_view(), name='order-list-create'),
    path('orders/<uuid:token>/', OrderDetailAPIView.as_view(), name='order-detail'),
    path('orders/<uuid:token>/cancel/', OrderCancelAPIView.as_view(), name='order-cancel'),
    path('orders/<uuid:token>/address/', OrderAddressUpdateAPIView.as_view(), name='order-address-update'),
    path('orders/<uuid:token>/items/', OrderItemCreateAPIView.as_view(), name='order-item-create'),
    path(
        'orders/<uuid:token>/items/<int:item_id>/',
        OrderItemUpdateDeleteAPIView.as_view(),
        name='order-item-update-delete',
    ),
    path('orders/<uuid:token>/pay/', PaymentCreateAPIView.as_view(), name='payment-create'),
    path('checkout/gateways/', ActiveGatewayListAPIView.as_view(), name='gateway-list'),
    path('payments/callback/<str:gateway_origin>/', PaymentCallbackAPIView.as_view(), name='payment-callback'),
]
