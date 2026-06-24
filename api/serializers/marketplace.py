"""Serializers para marketplace avançado: repasses, pedidos vendedor, reviews, devoluções, chat."""
from decimal import Decimal
from rest_framework import serializers
from api.models import (
    ProductReview, ReturnRequest, ReturnStatus, ProductConversation,
    ProductMessage, SellerPayout, VehicleBrand, VehicleModel,
    ProductVehicleCompatibility, OrderItem, ShippingStatus,
)


class SellerPayoutSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    store_name = serializers.CharField(source='seller.store_name', read_only=True)

    class Meta:
        model = SellerPayout
        fields = [
            'id', 'amount', 'pix_key', 'status', 'status_display', 'admin_notes',
            'payment_reference', 'processed_at', 'created_at', 'store_name',
        ]
        read_only_fields = ['status', 'admin_notes', 'payment_reference', 'processed_at']


class PayoutRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    pix_key = serializers.CharField(max_length=120, required=False, allow_blank=True)


class SellerPixKeySerializer(serializers.Serializer):
    pix_key = serializers.CharField(max_length=120)


class PayoutProcessSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['processing', 'paid', 'rejected'])
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    payment_reference = serializers.CharField(required=False, allow_blank=True)


class SellerOrderItemSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    order_status_display = serializers.CharField(source='order.get_status_display', read_only=True)
    order_created_at = serializers.DateTimeField(source='order.created_at', read_only=True)
    customer_name = serializers.CharField(source='order.customer_name', read_only=True)
    customer_phone = serializers.CharField(source='order.customer_phone', read_only=True)
    shipping_address = serializers.CharField(source='order.shipping_address', read_only=True)
    shipping_city = serializers.CharField(source='order.shipping_city', read_only=True)
    shipping_state = serializers.CharField(source='order.shipping_state', read_only=True)
    shipping_zip = serializers.CharField(source='order.shipping_zip', read_only=True)
    delivery_method = serializers.CharField(source='order.delivery_method', read_only=True)
    item_shipping_status_display = serializers.CharField(
        source='get_item_shipping_status_display', read_only=True,
    )
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    tracking_url = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order_id', 'order_status', 'order_status_display', 'order_created_at',
            'product_name', 'product_sku', 'unit_price', 'quantity', 'subtotal',
            'seller_earning', 'platform_fee', 'image_url',
            'customer_name', 'customer_phone', 'shipping_address', 'shipping_city',
            'shipping_state', 'shipping_zip', 'delivery_method',
            'item_shipping_status', 'item_shipping_status_display',
            'item_tracking_code', 'item_carrier', 'item_shipped_at', 'tracking_url',
        ]

    def get_tracking_url(self, obj):
        code = (obj.item_tracking_code or '').strip()
        if not code:
            return ''
        if code.startswith('http'):
            return code
        return f'https://rastreamento.correios.com.br/app/index.php?objeto={code}'


class SellerShippingUpdateSerializer(serializers.Serializer):
    item_shipping_status = serializers.ChoiceField(choices=ShippingStatus.choices, required=False)
    item_tracking_code = serializers.CharField(max_length=80, required=False, allow_blank=True)
    item_carrier = serializers.CharField(max_length=80, required=False, allow_blank=True)


class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = ProductReview
        fields = [
            'id', 'rating', 'title', 'comment', 'is_verified_purchase',
            'user_name', 'created_at',
        ]


class ProductReviewCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    order_item_id = serializers.IntegerField(required=False, allow_null=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(max_length=120, required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)


class VehicleModelSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    brand_slug = serializers.CharField(source='brand.slug', read_only=True)

    class Meta:
        model = VehicleModel
        fields = ['id', 'name', 'slug', 'brand_name', 'brand_slug', 'year_start', 'year_end']


class VehicleBrandSerializer(serializers.ModelSerializer):
    models = VehicleModelSerializer(many=True, read_only=True)

    class Meta:
        model = VehicleBrand
        fields = ['id', 'name', 'slug', 'models']


class VehicleBrandListSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = ['id', 'name', 'slug']


class ProductVehicleCompatWriteSerializer(serializers.Serializer):
    vehicle_model_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True,
    )


class ReturnRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    product_name = serializers.CharField(source='order_item.product_name', read_only=True)
    order_id = serializers.IntegerField(source='order.id', read_only=True)

    class Meta:
        model = ReturnRequest
        fields = [
            'id', 'order_id', 'order_item_id', 'product_name', 'reason', 'description', 'status',
            'status_display', 'seller_response', 'refund_amount', 'return_tracking_code',
            'created_at', 'updated_at',
        ]


class ReturnRequestCreateSerializer(serializers.Serializer):
    order_item_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=80)
    description = serializers.CharField(required=False, allow_blank=True)


class ReturnStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ReturnStatus.choices)
    seller_response = serializers.CharField(required=False, allow_blank=True)
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    refund_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True,
    )
    return_tracking_code = serializers.CharField(required=False, allow_blank=True)


class ProductMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = ProductMessage
        fields = ['id', 'body', 'sender_name', 'is_mine', 'is_read', 'created_at']

    def get_is_mine(self, obj):
        req = self.context.get('request')
        if req and req.user.is_authenticated:
            return obj.sender_id == req.user.id
        return False


class ProductConversationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    seller_name = serializers.CharField(source='seller.store_name', read_only=True)
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ProductConversation
        fields = [
            'id', 'product_name', 'product_slug', 'seller_name', 'buyer_name',
            'last_message_at', 'unread_count', 'last_message',
        ]

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if not msg:
            return ''
        return msg.body[:120]


class ChatMessageCreateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000)


class ChatStartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    message = serializers.CharField(max_length=2000, required=False, allow_blank=True)
