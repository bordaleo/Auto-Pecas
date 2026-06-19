from decimal import Decimal
from django.utils import timezone
from api.models import Coupon, Order, OrderStatus


def validate_coupon(code, user, subtotal):
    """Valida cupom e retorna (coupon, discount_amount) ou levanta ValueError."""
    code = (code or '').strip().upper()
    if not code:
        raise ValueError('Informe o código do cupom.')

    try:
        coupon = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        raise ValueError('Cupom inválido.')

    if not coupon.is_active:
        raise ValueError('Cupom inativo.')
    if coupon.expires_at and coupon.expires_at < timezone.now():
        raise ValueError('Cupom expirado.')
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        raise ValueError('Cupom esgotado.')
    if subtotal < coupon.min_order_amount:
        raise ValueError(f'Pedido mínimo de R$ {coupon.min_order_amount:.2f} para este cupom.')
    if coupon.first_purchase_only and user:
        has_purchase = Order.objects.filter(user=user, status=OrderStatus.APPROVED).exists()
        if has_purchase:
            raise ValueError('Cupom válido apenas na primeira compra.')

    subtotal = Decimal(str(subtotal)).quantize(Decimal('0.01'))
    if coupon.discount_type == 'percent':
        discount = (subtotal * coupon.discount_value / Decimal('100')).quantize(Decimal('0.01'))
    else:
        discount = Decimal(str(coupon.discount_value)).quantize(Decimal('0.01'))

    discount = min(discount, subtotal)
    if discount <= 0:
        raise ValueError('Cupom sem desconto aplicável.')

    return coupon, discount


def apply_coupon_usage(coupon):
    coupon.used_count += 1
    coupon.save(update_fields=['used_count'])
