from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.orders.models import Order

@extend_schema(tags=['Checkout'])
class OrderStatusView(APIView):
    """
    GET /orders/<order_number>/

    Used by the frontend's success/failed pages (and safe to poll a few
    times right after redirect, in case the gateway callback is still a
    beat behind the browser redirect) to read the current state of an
    order without exposing the internal pk.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        order = Order.objects.filter(order_number=order_number, user=request.user).first()
        if order is None:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(
            {
                'order_number': order.order_number,
                'status': order.status,
                'total_amount': order.total_amount,
                'expires_at': order.expires_at,
                'paid_at': order.paid_at,
                'is_payable': order.is_payable,
            }
        )
