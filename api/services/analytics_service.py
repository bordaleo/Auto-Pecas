"""Analytics para vendedores."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Q, F
from django.utils import timezone

from api.models import Product, ProductViewEvent, OrderItem, OrderStatus


def get_seller_analytics(seller, days: int = 30) -> dict:
    since = timezone.now() - timedelta(days=days)
    stale_since = timezone.now() - timedelta(days=30)

    products = Product.objects.filter(seller=seller)
    product_ids = list(products.values_list('id', flat=True))

    views_by_product = {
        r['product_id']: r['views']
        for r in ProductViewEvent.objects.filter(
            product_id__in=product_ids, created_at__gte=since,
        ).values('product_id').annotate(views=Count('id'))
    }

    sales_by_product = {
        r['product_id']: {'count': r['sales'], 'revenue': r['revenue']}
        for r in OrderItem.objects.filter(
            seller=seller,
            product_id__in=product_ids,
            order__status=OrderStatus.APPROVED,
            order__created_at__gte=since,
        ).values('product_id').annotate(
            sales=Sum('quantity'),
            revenue=Sum(F('unit_price') * F('quantity')),
        )
    }

    product_stats = []
    for p in products.filter(is_active=True):
        views = views_by_product.get(p.id, 0)
        sales = sales_by_product.get(p.id, {})
        sales_count = sales.get('count') or 0
        conversion = round((sales_count / views * 100), 2) if views > 0 else 0
        product_stats.append({
            'id': p.id,
            'name': p.name,
            'slug': p.slug,
            'views': views,
            'sales': int(sales_count or 0),
            'revenue': str(sales.get('revenue') or Decimal('0.00')),
            'conversion_rate': conversion,
            'stock': p.stock,
            'created_at': p.created_at.isoformat(),
            'is_stale': p.created_at <= stale_since and (sales_count or 0) == 0,
        })

    product_stats.sort(key=lambda x: x['views'], reverse=True)
    stale = [p for p in product_stats if p['is_stale']]

    return {
        'period_days': days,
        'totals': {
            'products_active': products.filter(is_active=True).count(),
            'total_views': sum(views_by_product.values()),
            'total_sales': sum(int(s.get('count') or 0) for s in sales_by_product.values()),
            'stale_products': len(stale),
        },
        'products': product_stats[:50],
        'stale_products': stale[:20],
    }
