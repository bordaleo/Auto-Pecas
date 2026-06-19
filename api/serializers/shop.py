from rest_framework import serializers
from decimal import Decimal
from api.models import Order, OrderItem, Product, DeliveryMethod


class CartItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class ShippingQuoteSerializer(serializers.Serializer):
    delivery_method = serializers.ChoiceField(choices=DeliveryMethod.choices, default=DeliveryMethod.DELIVERY)
    shipping_zip = serializers.CharField(max_length=12, required=False, allow_blank=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'))


class CheckoutSerializer(serializers.Serializer):
    items = CartItemInputSerializer(many=True)
    customer_name = serializers.CharField(max_length=255)
    customer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    order_email = serializers.EmailField(required=False, allow_blank=True)
    delivery_method = serializers.ChoiceField(choices=DeliveryMethod.choices, default=DeliveryMethod.DELIVERY)
    shipping_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    shipping_city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    shipping_state = serializers.CharField(max_length=2, required=False, allow_blank=True)
    shipping_zip = serializers.CharField(max_length=12, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('O carrinho está vazio.')
        return value

    def validate(self, attrs):
        delivery_method = attrs.get('delivery_method', DeliveryMethod.DELIVERY)
        if delivery_method == DeliveryMethod.DELIVERY:
            missing = []
            if not (attrs.get('shipping_zip') or '').strip():
                missing.append('CEP')
            if not (attrs.get('shipping_address') or '').strip():
                missing.append('endereço')
            if not (attrs.get('shipping_city') or '').strip():
                missing.append('cidade')
            if not (attrs.get('shipping_state') or '').strip():
                missing.append('UF')
            if missing:
                raise serializers.ValidationError(
                    {'shipping_address': f'Para entrega, informe: {", ".join(missing)}.'}
                )
        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_sku', 'unit_price', 'quantity', 'image_url', 'subtotal']


class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'))


class CartSyncSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    email = serializers.EmailField(required=False, allow_blank=True)


class ShopOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delivery_method_display = serializers.CharField(source='get_delivery_method_display', read_only=True)
    shipping_status_display = serializers.CharField(source='get_shipping_status_display', read_only=True)
    subtotal = serializers.SerializerMethodField()
    tracking_url = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_display', 'amount', 'subtotal', 'shipping_fee',
            'discount_amount', 'coupon_code',
            'delivery_method', 'delivery_method_display',
            'shipping_status', 'shipping_status_display', 'tracking_code', 'carrier',
            'tracking_url', 'shipped_at',
            'payment_method', 'payment_id', 'payment_preference_id', 'order_email',
            'customer_name', 'customer_phone', 'shipping_address', 'shipping_city',
            'shipping_state', 'shipping_zip', 'notes', 'items', 'created_at', 'updated_at',
        ]

    def get_subtotal(self, obj):
        return obj.amount - (obj.shipping_fee or Decimal('0.00')) + (obj.discount_amount or Decimal('0.00'))

    def get_tracking_url(self, obj):
        code = (obj.tracking_code or '').strip()
        if not code:
            return ''
        if code.startswith('http'):
            return code
        return f'https://rastreamento.correios.com.br/app/index.php?objeto={code}'


class ShopPaymentPreferenceSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
