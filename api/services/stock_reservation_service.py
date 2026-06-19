"""Reserva temporária de estoque durante checkout pendente."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from api.models import Product, StockReservation, SystemConfig


def _reservation_minutes() -> int:
    config = SystemConfig.get_config()
    return int(config.stock_reservation_minutes or 30)


def get_reserved_quantity(product_id: int, exclude_order_id: int | None = None) -> int:
    """Quantidade reservada ativa para um produto."""
    now = timezone.now()
    qs = StockReservation.objects.filter(
        product_id=product_id,
        released=False,
        expires_at__gt=now,
    )
    if exclude_order_id:
        qs = qs.exclude(order_id=exclude_order_id)
    total = qs.aggregate(total=Sum('quantity'))['total']
    return int(total or 0)


def get_available_stock(product: Product, exclude_order_id: int | None = None) -> int:
    reserved = get_reserved_quantity(product.id, exclude_order_id=exclude_order_id)
    return max(0, product.stock - reserved)


def release_expired_reservations() -> int:
    """Libera reservas expiradas. Retorna quantidade liberada."""
    now = timezone.now()
    updated = StockReservation.objects.filter(
        released=False,
        expires_at__lte=now,
    ).update(released=True)
    return updated


def release_order_reservations(order_id: int) -> None:
    StockReservation.objects.filter(order_id=order_id, released=False).update(released=True)


def create_reservations_for_order(order, user, items: list[dict]) -> None:
    """Cria reservas ao criar pedido pendente. items: [{product, quantity}, ...]"""
    release_expired_reservations()
    expires = timezone.now() + timedelta(minutes=_reservation_minutes())
    for item in items:
        StockReservation.objects.create(
            product=item['product'],
            order=order,
            user=user,
            quantity=item['quantity'],
            expires_at=expires,
        )


def consume_order_reservations(order_id: int) -> None:
    """Marca reservas como liberadas após venda confirmada (estoque já decrementado)."""
    release_order_reservations(order_id)
