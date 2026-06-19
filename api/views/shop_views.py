from decimal import Decimal
from django.db import transaction
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from api.models import Order, OrderItem, OrderStatus, Product, DeliveryMethod, SystemConfig
from api.serializers.shop import (
    CheckoutSerializer,
    ShopOrderSerializer,
    ShopPaymentPreferenceSerializer,
    ShippingQuoteSerializer,
    CouponValidateSerializer,
    CartSyncSerializer,
)
from api.services.payment_service import payment_service
from api.services.email_service import email_service
from api.services.shipping_service import calculate_shipping_fee, get_pickup_address
from api.services.marketplace_service import split_sale_amount
from api.services.coupon_service import validate_coupon, apply_coupon_usage
from api.services.abandoned_cart_service import sync_abandoned_cart, mark_cart_recovered
import logging

logger = logging.getLogger(__name__)


class ShippingQuoteView(APIView):
    """Calcula frete antes do checkout."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ShippingQuoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        config = SystemConfig.get_config()
        fee, is_free, pickup_address = calculate_shipping_fee(
            data['delivery_method'],
            data['subtotal'],
            data.get('shipping_zip', ''),
        )
        if fee is None:
            return Response({
                'shipping_fee': '0.00',
                'is_free': False,
                'needs_zip': True,
                'free_shipping_min': str(config.free_shipping_min),
                'pickup_address': pickup_address,
                'delivery_method': data['delivery_method'],
                'detail': 'Informe um CEP válido (8 dígitos) para calcular o frete.',
            })

        return Response({
            'shipping_fee': str(fee),
            'is_free': is_free,
            'free_shipping_min': str(config.free_shipping_min),
            'pickup_address': pickup_address,
            'delivery_method': data['delivery_method'],
        })


class CouponValidateView(APIView):
    """Valida cupom antes do checkout."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        try:
            coupon, discount = validate_coupon(
                data['code'], request.user, data['subtotal'],
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'code': coupon.code,
            'discount_amount': str(discount),
            'discount_type': coupon.discount_type,
            'discount_value': str(coupon.discount_value),
            'first_purchase_only': coupon.first_purchase_only,
        })


class CartSyncView(APIView):
    """Sincroniza carrinho para recuperação por e-mail."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CartSyncSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        email = data.get('email') or request.user.email
        cart = sync_abandoned_cart(request.user, email, data['items'])
        if not cart:
            return Response({'detail': 'Carrinho vazio.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True, 'subtotal': str(cart.subtotal)})


class CheckoutView(APIView):
    """Cria pedido a partir do carrinho (antes do pagamento)."""
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        subtotal = Decimal('0.00')
        order_items_data = []

        for item in data['items']:
            try:
                product = Product.objects.select_for_update().get(
                    id=item['product_id'], is_active=True
                )
            except Product.DoesNotExist:
                return Response(
                    {'detail': f'Peça #{item["product_id"]} não encontrada.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            qty = item['quantity']
            if product.stock < qty:
                return Response(
                    {'detail': f'Estoque insuficiente para "{product.name}". Disponível: {product.stock}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            line_total = product.price * qty
            subtotal += line_total
            line_gross = line_total
            platform_fee, seller_earning, _ = split_sale_amount(line_gross, product.seller)
            order_items_data.append({
                'product': product,
                'seller': product.seller,
                'product_name': product.name,
                'product_sku': product.sku,
                'unit_price': product.price,
                'quantity': qty,
                'image_url': product.image_url,
                'platform_fee': platform_fee,
                'seller_earning': seller_earning,
            })

        delivery_method = data.get('delivery_method', DeliveryMethod.DELIVERY)
        shipping_fee, _, pickup_address = calculate_shipping_fee(
            delivery_method,
            subtotal,
            data.get('shipping_zip', ''),
        )
        if shipping_fee is None:
            return Response(
                {'detail': 'CEP inválido para calcular o frete.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shipping_address = data.get('shipping_address', '')
        shipping_city = data.get('shipping_city', '')
        shipping_state = data.get('shipping_state', '')
        shipping_zip = data.get('shipping_zip', '')

        if delivery_method == DeliveryMethod.PICKUP:
            shipping_address = pickup_address
            shipping_city = shipping_city or 'Retirada na loja'
            shipping_state = shipping_state or 'SP'
            shipping_zip = shipping_zip or ''

        total = subtotal + shipping_fee
        discount_amount = Decimal('0.00')
        coupon_code = ''
        coupon_obj = None

        coupon_input = (data.get('coupon_code') or '').strip()
        if coupon_input:
            try:
                coupon_obj, discount_amount = validate_coupon(
                    coupon_input, request.user, subtotal,
                )
                coupon_code = coupon_obj.code
            except ValueError as e:
                return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            total = max(Decimal('0.01'), total - discount_amount)

        order = Order.objects.create(
            user=request.user,
            status=OrderStatus.PENDING,
            amount=total,
            shipping_fee=shipping_fee,
            delivery_method=delivery_method,
            discount_amount=discount_amount,
            coupon_code=coupon_code,
            order_email=data.get('order_email') or request.user.email,
            customer_name=data['customer_name'],
            customer_phone=data.get('customer_phone', ''),
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_state=shipping_state,
            shipping_zip=shipping_zip,
            notes=data.get('notes', ''),
        )

        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)

        if coupon_obj:
            apply_coupon_usage(coupon_obj)

        mark_cart_recovered(request.user.email)

        return Response(ShopOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class ShopPaymentPreferenceView(APIView):
    """Cria preferência Mercado Pago para pedido de autopeças."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ShopPaymentPreferenceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order_id = serializer.validated_data['order_id']
        try:
            order = Order.objects.prefetch_related('items').get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Pedido não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if order.status == OrderStatus.APPROVED:
            return Response({'detail': 'Pedido já pago.'}, status=status.HTTP_400_BAD_REQUEST)

        items = []
        items_subtotal = sum(float(item.unit_price) * item.quantity for item in order.items.all())
        discount = float(order.discount_amount or 0)
        discount_ratio = (discount / items_subtotal) if items_subtotal > 0 and discount > 0 else 0

        for item in order.items.all():
            unit = float(item.unit_price)
            if discount_ratio > 0:
                unit = round(unit * (1 - discount_ratio), 2)
            items.append({
                'title': item.product_name[:256],
                'quantity': item.quantity,
                'unit_price': unit,
            })

        if order.shipping_fee and order.shipping_fee > 0:
            items.append({
                'title': 'Frete',
                'quantity': 1,
                'unit_price': float(order.shipping_fee),
            })

        # Garante que a soma dos itens = valor do pedido (evita 400 no Payment Brick)
        items_total = round(sum(i['quantity'] * i['unit_price'] for i in items), 2)
        order_total = round(float(order.amount), 2)
        diff = round(order_total - items_total, 2)
        if diff != 0:
            items.append({
                'title': 'Ajuste',
                'quantity': 1,
                'unit_price': diff,
            })

        external_reference = f"order_{order.id}_user_{request.user.id}"
        preference = payment_service.create_shop_payment_preference(
            items=items,
            amount=order.amount,
            user_id=request.user.id,
            user_name=order.customer_name or request.user.name,
            user_email=order.order_email or request.user.email,
            external_reference=external_reference,
        )

        if not preference:
            return Response(
                {'detail': 'Erro ao criar preferência de pagamento.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        order.payment_preference_id = preference.get('id')
        order.save(update_fields=['payment_preference_id', 'updated_at'])

        return Response({
            'preference_id': preference.get('id'),
            'init_point': preference.get('init_point'),
            'sandbox_init_point': preference.get('sandbox_init_point'),
            'order_id': order.id,
            'amount': str(order.amount),
            'brick_amount': float(order.amount),
        })


class ShopOrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')
        return Response(ShopOrderSerializer(orders, many=True).data)


class ShopOrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.prefetch_related('items').get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Pedido não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ShopOrderSerializer(order).data)


def approve_shop_order(order):
    """Marca pedido como aprovado e decrementa estoque."""
    if order.status == OrderStatus.APPROVED:
        return
    with transaction.atomic():
        order.status = OrderStatus.APPROVED
        order.save(update_fields=['status', 'updated_at'])
        for item in order.items.select_related('product').all():
            if item.product_id:
                product = Product.objects.select_for_update().get(pk=item.product_id)
                product.stock = max(0, product.stock - item.quantity)
                product.save(update_fields=['stock', 'updated_at'])
    try:
        email_service.send_order_confirmation(order)
    except Exception as e:
        logger.error('Erro ao enviar email de confirmação do pedido #%s: %s', order.id, e)
