from decimal import Decimal
from django.db.models import Sum
from api.models import SystemConfig, Seller


def get_commission_rate(seller=None):
    """Percentual retido pela Galelugi (0–100)."""
    if seller and seller.commission_rate is not None:
        return seller.commission_rate
    config = SystemConfig.get_config()
    return getattr(config, 'marketplace_commission_percent', None) or Decimal('12.00')


def split_sale_amount(gross_amount, seller=None):
    """Divide valor da venda entre plataforma e vendedor."""
    gross = Decimal(str(gross_amount)).quantize(Decimal('0.01'))
    rate = get_commission_rate(seller)
    platform_fee = (gross * rate / Decimal('100')).quantize(Decimal('0.01'))
    seller_earning = (gross - platform_fee).quantize(Decimal('0.01'))
    return platform_fee, seller_earning, rate


def seller_dashboard_stats(seller):
    from api.models import OrderItem, OrderStatus
    products = seller.products.all()
    active_count = products.filter(is_active=True).count()
    sold = (
        OrderItem.objects.filter(
            seller=seller,
            order__status=OrderStatus.APPROVED,
        ).aggregate(
            total=Sum('seller_earning'),
            gross=Sum('unit_price'),
        )
    )
    return {
        'products_total': products.count(),
        'products_active': active_count,
        'sales_gross': str(sold['gross'] or Decimal('0.00')),
        'sales_earnings': str(sold['total'] or Decimal('0.00')),
        'commission_rate': str(get_commission_rate(seller)),
    }
