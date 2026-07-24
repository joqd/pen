from ..services.cart_service import CartService


class CartMixin:
    CART_HEADER = 'cart_token'

    def get_cart(self, request):
        if request.user.is_authenticated:
            return CartService.get_or_create_cart(user=request.user)

        token = request.COOKIES.get(self.CART_HEADER)

        return CartService.get_or_create_cart(token=token)
