"""Métricas do painel operacional — Galelugi Peças."""
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
        "store": "Galelugi Peças",
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


def get_painel_dashboard_slice(page: str, days: int = 14) -> dict:
    """Dados por aba do painel operacional."""
    payload = get_admin_dashboard_payload(days=days)
    totals = payload["totals"]

    if page == "pedidos":
        from api.models import Seller, ShippingStatus

        orders = list(
            Order.objects.select_related("user")
            .order_by("-created_at")[:50]
            .values(
                "id", "status", "amount", "customer_name", "created_at",
                "shipping_status", "tracking_code", "carrier", "shipping_fee",
                "user__email",
            )
        )
        return {
            "page": page,
            "period_days": days,
            "totals": totals,
            "orders": orders,
            "shipping_status_choices": [
                {"value": c[0], "label": c[1]} for c in ShippingStatus.choices
            ],
        }

    if page == "pagamentos":
        from api.models import OrderStatus

        recent = list(
            Order.objects.filter(status=OrderStatus.APPROVED)
            .order_by("-updated_at")[:30]
            .values("id", "amount", "payment_method", "payment_id", "customer_name", "created_at")
        )
        return {
            "page": page,
            "period_days": days,
            "totals": totals,
            "payments": recent,
            "sales_by_day": payload["sales_by_day"],
        }

    if page == "conteudo":
        from api.models import Product, Seller

        return {
            "page": page,
            "period_days": days,
            "totals": totals,
            "top_products": payload["top_products"],
            "sellers_pending": Seller.objects.filter(status=Seller.Status.PENDING).count(),
            "products_inactive": Product.objects.filter(is_active=False).count(),
        }

    if page == "audiencia":
        from api.models import AbandonedCart, Seller

        return {
            "page": page,
            "period_days": days,
            "totals": totals,
            "abandoned_carts": AbandonedCart.objects.filter(recovered_at__isnull=True).count(),
            "sellers_active": Seller.objects.filter(status=Seller.Status.ACTIVE).count(),
            "sales_by_day": payload["sales_by_day"],
        }

    if page == "financeiro":
        from api.services.finance_service import get_platform_finance_payload
        finance = get_platform_finance_payload(days=days)
        return {"page": page, "period_days": days, "totals": totals, **finance}

    return {
        "page": "visao",
        "period_days": days,
        "totals": totals,
        "sales_by_day": payload["sales_by_day"],
        "recent_orders": payload["recent_orders"],
        "top_products": payload["top_products"][:5],
        "part_requests": get_part_request_admin_metrics(days=days),
    }


def get_part_request_admin_metrics(days: int = 30) -> dict:
    from api.services.part_request_service import get_part_request_admin_metrics as _metrics
    return _metrics(days=days)
