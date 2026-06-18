from rest_framework import serializers
from api.models import Order, OrderStatus
from api.serializers.user import UserSerializer
from api.serializers.shop import OrderItemSerializer


class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'user', 'status', 'status_display',
            'payment_method', 'payment_id', 'payment_preference_id', 'order_email',
            'customer_name', 'customer_phone', 'shipping_address', 'shipping_city',
            'shipping_state', 'shipping_zip', 'delivery_method', 'shipping_fee',
            'notes', 'amount', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['customer_name', 'order_email']
