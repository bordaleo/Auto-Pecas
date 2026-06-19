"""Métricas financeiras da plataforma — lucro, comissões, repasses."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from api.models import Order, OrderItem, OrderStatus, PayoutStatus, Product, SellerPayout


def get_platform_finance_payload(days: int = 30) -> dict:
    since = timezone.now() - timedelta(days=days)
    approved_orders = Order.objects.filter(
        status=OrderStatus.APPROVED,
        created_at__gte=since,
    )
    approved_items = OrderItem.objects.filter(
        order__status=OrderStatus.APPROVED,
        order__created_at__gte=since,
    )

    gross_revenue = approved_orders.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    shipping_revenue = approved_orders.aggregate(t=Sum('shipping_fee'))['t'] or Decimal('0')

    marketplace_items = approved_items.filter(seller__isnull=False)
    platform_commission = marketplace_items.aggregate(t=Sum('platform_fee'))['t'] or Decimal('0')
    seller_earnings_total = marketplace_items.aggregate(t=Sum('seller_earning'))['t'] or Decimal('0')

    own_items = approved_items.filter(seller__isnull=True)
    own_revenue = own_items.aggregate(
        t=Sum(F('unit_price') * F('quantity')),
    )['t'] or Decimal('0')
    own_cost = own_items.filter(product__isnull=False).aggregate(
        t=Sum(F('product__cost_price') * F('quantity')),
    )['t']
    own_cost = own_cost or Decimal('0')
    own_margin = own_revenue - own_cost

    pending_payouts = SellerPayout.objects.filter(
        status__in=[PayoutStatus.PENDING, PayoutStatus.PROCESSING],
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    sellers_balance = OrderItem.objects.filter(
        seller__isnull=False,
        order__status=OrderStatus.APPROVED,
        seller_balance_credited=True,
    ).aggregate(
        credited=Sum('seller_earning'),
    )['credited'] or Decimal('0')

    paid_out = SellerPayout.objects.filter(status=PayoutStatus.PAID).aggregate(
        t=Sum('amount'),
    )['t'] or Decimal('0')

    platform_profit_estimate = platform_commission + own_margin + shipping_revenue

    commission_by_day = list(
        marketplace_items.annotate(day=TruncDate('order__created_at'))
        .values('day')
        .annotate(commission=Sum('platform_fee'), seller_earning=Sum('seller_earning'))
        .order_by('day')
    )

    return {
        'period_days': days,
        'gross_revenue': str(gross_revenue),
        'shipping_revenue': str(shipping_revenue),
        'platform_commission': str(platform_commission),
        'seller_earnings_accrued': str(seller_earnings_total),
        'own_store_revenue': str(own_revenue),
        'own_store_cost': str(own_cost),
        'own_store_margin': str(own_margin),
        'platform_profit_estimate': str(platform_profit_estimate),
        'pending_payouts': str(pending_payouts),
        'total_paid_to_sellers': str(paid_out),
        'seller_balance_outstanding': str(sellers_balance - paid_out - pending_payouts),
        'commission_by_day': [
            {
                'day': str(r['day']),
                'commission': str(r['commission'] or 0),
                'seller_earning': str(r['seller_earning'] or 0),
            }
            for r in commission_by_day
        ],
        'recent_payouts': list(
            SellerPayout.objects.select_related('seller')
            .order_by('-created_at')[:20]
            .values(
                'id', 'amount', 'status', 'pix_key', 'created_at', 'processed_at',
                'seller__store_name',
            )
        ),
    }
