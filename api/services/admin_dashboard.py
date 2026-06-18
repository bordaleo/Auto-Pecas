"""Métricas do painel operacional — AutoPeças Sandroni."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from api.models import Category, Order, OrderStatus, Product, User


def get_admin_dashboard_payload(days: int = 14) -> dict:
    since = timezone.now() - timedelta(days=days)
    orders = Order.objects.filter(created_at__gte=since)
    approved = orders.filter(status=OrderStatus.APPROVED)

    revenue = approved.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    pending = orders.filter(status=OrderStatus.PENDING).count()
    rejected = orders.filter(status=OrderStatus.REJECTED).count()

    sales_by_day = list(
        approved.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"), revenue=Sum("amount"))
        .order_by("day")
    )

    top_products = list(
        Product.objects.filter(is_active=True)
        .order_by("-stock")[:10]
        .values("id", "name", "sku", "stock", "price")
    )

    return {
        "store": "AutoPeças Sandroni",
        "period_days": days,
        "totals": {
            "users": User.objects.count(),
            "products": Product.objects.filter(is_active=True).count(),
            "categories": Category.objects.filter(is_active=True).count(),
            "orders": orders.count(),
            "orders_approved": approved.count(),
            "orders_pending": pending,
            "orders_rejected": rejected,
            "revenue": str(revenue),
        },
        "sales_by_day": [
            {"day": str(r["day"]), "count": r["count"], "revenue": str(r["revenue"] or 0)}
            for r in sales_by_day
        ],
        "top_products": top_products,
        "recent_orders": list(
            Order.objects.select_related("user")
            .order_by("-created_at")[:15]
            .values("id", "status", "amount", "customer_name", "created_at", "user__email")
        ),
    }
