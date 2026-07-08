from django.urls import path

from .views.cart_views import (
    CartView,
    CartItemCreateView,
    CartItemUpdateView,
    CartItemDeleteView,
)

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/items/', CartItemCreateView.as_view(), name='cart-add-item'),
    path('cart/items/<int:item_id>/', CartItemUpdateView.as_view(), name='cart-update-item'),
    path('cart/items/<int:item_id>/', CartItemDeleteView.as_view(), name='cart-delete-item'),
]