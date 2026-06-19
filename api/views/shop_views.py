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
from api.services.shipping_service import get_pickup_address
from api.services.melhor_envio_service import calculate_shipping_with_provider
from api.services.marketplace_service import split_sale_amount
from api.services.checkout_service import build_order_items_from_request, create_orders_from_cart
from api.services.stock_reservation_service import release_order_reservations
from api.services.payout_service import credit_seller_earnings_for_order
from api.services.notification_service import notify_buyer_order_paid, notify_seller_new_order
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
        cart_items = data.get('cart_items') or []
        fee, is_free, pickup_address, meta = calculate_shipping_with_provider(
            data['delivery_method'],
            data['subtotal'],
            data.get('shipping_zip', ''),
            cart_items=cart_items or None,
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
            'shipping_service_name': meta.get('service_name', ''),
            'shipping_days': meta.get('days'),
            'shipping_provider': meta.get('provider', 'fixed'),
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
    """Cria pedido(s) por loja a partir do carrinho (multi-vendedor)."""
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            order_items_data = build_order_items_from_request(data, request.user)
        except Product.DoesNotExist:
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = sum(i['unit_price'] * i['quantity'] for i in order_items_data)
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

        try:
            order_group, orders, primary = create_orders_from_cart(
                request.user, data, order_items_data, discount_amount, coupon_code,
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if coupon_obj:
            apply_coupon_usage(coupon_obj)

        mark_cart_recovered(request.user.email)

        payload = ShopOrderSerializer(primary).data
        payload['order_group_id'] = order_group.id
        payload['orders_count'] = len(orders)
        payload['total_amount'] = str(order_group.amount)
        payload['sub_orders'] = ShopOrderSerializer(orders, many=True).data
        return Response(payload, status=status.HTTP_201_CREATED)


class ShopPaymentPreferenceView(APIView):
    """Cria preferência Mercado Pago para pedido de autopeças."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ShopPaymentPreferenceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order_id = serializer.validated_data['order_id']
        try:
            order = Order.objects.prefetch_related('items', 'order_group').get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Pedido não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        group = order.order_group
        if group and group.status == OrderStatus.APPROVED:
            return Response({'detail': 'Pedido já pago.'}, status=status.HTTP_400_BAD_REQUEST)
        if not group and order.status == OrderStatus.APPROVED:
            return Response({'detail': 'Pedido já pago.'}, status=status.HTTP_400_BAD_REQUEST)

        orders = list(
            group.orders.prefetch_related('items').all() if group else [order]
        )
        pay_amount = group.amount if group else order.amount

        items = []
        for sub in orders:
            seller_label = sub.fulfillment_seller.store_name if sub.fulfillment_seller_id else 'Galelugi'
            for item in sub.items.all():
                items.append({
                    'title': f'[{seller_label}] {item.product_name}'[:256],
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                })
            if sub.shipping_fee and sub.shipping_fee > 0:
                items.append({
                    'title': f'Frete — {seller_label}'[:256],
                    'quantity': 1,
                    'unit_price': float(sub.shipping_fee),
                })

        if group and group.discount_amount and group.discount_amount > 0:
            items.append({
                'title': 'Desconto',
                'quantity': 1,
                'unit_price': -float(group.discount_amount),
            })

        items_total = round(sum(i['quantity'] * i['unit_price'] for i in items), 2)
        order_total = round(float(pay_amount), 2)
        diff = round(order_total - items_total, 2)
        if diff != 0:
            items.append({'title': 'Ajuste', 'quantity': 1, 'unit_price': diff})

        ref_id = group.id if group else order.id
        ref_prefix = 'group' if group else 'order'
        external_reference = f'{ref_prefix}_{ref_id}_user_{request.user.id}'
        preference = payment_service.create_shop_payment_preference(
            items=items,
            amount=pay_amount,
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

        pref_id = preference.get('id')
        if group:
            group.payment_preference_id = pref_id
            group.save(update_fields=['payment_preference_id', 'updated_at'])
            Order.objects.filter(order_group=group).update(payment_preference_id=pref_id)
        else:
            order.payment_preference_id = pref_id
            order.save(update_fields=['payment_preference_id', 'updated_at'])

        return Response({
            'preference_id': pref_id,
            'init_point': preference.get('init_point'),
            'sandbox_init_point': preference.get('sandbox_init_point'),
            'order_id': order.id,
            'order_group_id': group.id if group else None,
            'amount': str(pay_amount),
            'brick_amount': float(pay_amount),
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


def _orders_in_payment_scope(order):
    if order.order_group_id:
        return list(order.order_group.orders.all())
    return [order]


def reject_shop_order(order):
    """Rejeita pedido (e grupo) e libera reservas."""
    for sub in _orders_in_payment_scope(order):
        if sub.status == OrderStatus.REJECTED:
            continue
        sub.status = OrderStatus.REJECTED
        sub.save(update_fields=['status', 'updated_at'])
        release_order_reservations(sub.id)
    if order.order_group_id:
        from api.models import OrderGroup
        OrderGroup.objects.filter(pk=order.order_group_id).update(status=OrderStatus.REJECTED)


def _approve_single_order(sub):
    if sub.status == OrderStatus.APPROVED:
        return
    sub.status = OrderStatus.APPROVED
    sub.save(update_fields=['status', 'updated_at'])
    for item in sub.items.select_related('product').all():
        if item.product_id:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            product.stock = max(0, product.stock - item.quantity)
            product.save(update_fields=['stock', 'updated_at'])
    credit_seller_earnings_for_order(sub)
    release_order_reservations(sub.id)
    if sub.fulfillment_seller_id:
        item_count = sub.items.count()
        notify_seller_new_order(sub.fulfillment_seller, sub, item_count)


def approve_shop_order(order):
    """Aprova pedido ou grupo inteiro."""
    if order.order_group_id and order.order_group.status == OrderStatus.APPROVED:
        return
    if not order.order_group_id and order.status == OrderStatus.APPROVED:
        return

    with transaction.atomic():
        for sub in _orders_in_payment_scope(order):
            _approve_single_order(sub)
        if order.order_group_id:
            from api.models import OrderGroup
            OrderGroup.objects.filter(pk=order.order_group_id).update(status=OrderStatus.APPROVED)

    notify_buyer_order_paid(order)
    try:
        email_service.send_order_confirmation(order)
    except Exception as e:
        logger.error('Erro ao enviar email de confirmação do pedido #%s: %s', order.id, e)
