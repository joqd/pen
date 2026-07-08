from django.urls import path

from .views.cart_views import (
    CartView,
    CartItemCreateView,
    CartItemView,
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/', CartItemCreateView.as_view(), name='cart-add-item'),
    path('cart/items/<str:sku>/', CartItemView.as_view(), name='cart-item'),
]