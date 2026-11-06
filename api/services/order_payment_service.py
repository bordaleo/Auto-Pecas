"""Transições de pagamento de pedidos (aprovação, rejeição, estorno)."""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.utils import timezone

from api.models import Coupon, Order, OrderGroup, OrderStatus, Product
from api.services.email_service import email_service
from api.services.notification_service import notify_buyer_order_paid, notify_seller_new_order
from api.services.payout_service import credit_seller_earnings_for_order
from api.services.stock_reservation_service import release_order_reservations

logger = logging.getLogger(__name__)

MP_FAILED_STATUSES = frozenset({'rejected', 'cancelled'})
MP_REVERSED_STATUSES = frozenset({'refunded', 'charged_back'})


def payable_amount(order) -> Decimal:
    """Valor a cobrar: o grupo inteiro (multi-vendedor) ou o pedido avulso."""
    if order.order_group_id:
        return order.order_group.amount
    return order.amount


def orders_in_payment_scope(order) -> list:
    if order.order_group_id:
        return list(order.order_group.orders.all())
    return [order]


def _lock_payment_scope(order) -> tuple[OrderGroup | None, list]:
    """Trava grupo e sub-pedidos; deve ser chamado dentro de transaction.atomic()."""
    if order.order_group_id:
        group = OrderGroup.objects.select_for_update().get(pk=order.order_group_id)
        orders = list(
            Order.objects.select_for_update().filter(order_group_id=group.pk).order_by('pk')
        )
        return group, orders
    return None, [Order.objects.select_for_update().get(pk=order.pk)]


def _is_approved(group, orders) -> bool:
    if group is not None:
        return group.status == OrderStatus.APPROVED
    return all(o.status == OrderStatus.APPROVED for o in orders)


def _sync_payment_ids(group, orders, payment_id: str, payment_method: str) -> None:
    if not payment_id:
        return
    for obj in ([group] if group is not None else []) + orders:
        new_method = payment_method or obj.payment_method
        if obj.payment_id == payment_id and obj.payment_method == new_method:
            continue
        obj.payment_id = payment_id
        obj.payment_method = new_method
        obj.save(update_fields=['payment_id', 'payment_method', 'updated_at'])


def _set_scope_status(group, orders, new_status) -> None:
    for sub in orders:
        if sub.status != new_status:
            sub.status = new_status
            sub.save(update_fields=['status', 'updated_at'])
    if group is not None and group.status != new_status:
        group.status = new_status
        group.save(update_fields=['status', 'updated_at'])


def _approve_single_order(sub) -> None:
    sub.status = OrderStatus.APPROVED
    sub.save(update_fields=['status', 'updated_at'])
    now = timezone.now()
    for item in sub.items.all():
        if item.product_id:
            Product.objects.filter(pk=item.product_id).update(
                stock=Greatest(F('stock') - item.quantity, Value(0)),
                updated_at=now,
            )
    credit_seller_earnings_for_order(sub)
    release_order_reservations(sub.id)


def _count_coupon_usage(coupon_code: str) -> None:
    if coupon_code:
        Coupon.objects.filter(code__iexact=coupon_code).update(used_count=F('used_count') + 1)


def _send_paid_notifications(order_id: int) -> None:
    order = Order.objects.select_related('user', 'order_group').get(pk=order_id)
    for sub in orders_in_payment_scope(order):
        if sub.fulfillment_seller_id:
            notify_seller_new_order(sub.fulfillment_seller, sub, sub.items.count())
    notify_buyer_order_paid(order)
    try:
        email_service.send_order_confirmation(order)
    except Exception as e:
        logger.error('Erro ao enviar email de confirmação do pedido #%s: %s', order.id, e)


def approve_shop_order(order, payment_id: str = '', payment_method: str = '') -> bool:
    """Aprova pedido ou grupo inteiro. Idempotente; retorna True só na primeira aprovação."""
    with transaction.atomic():
        group, orders = _lock_payment_scope(order)
        if _is_approved(group, orders):
            current = (group.payment_id if group is not None else orders[0].payment_id) or ''
            if payment_id and current and payment_id != current:
                logger.error(
                    'Possível cobrança duplicada: pedido #%s já aprovado pelo pagamento %s, '
                    'novo pagamento aprovado %s.',
                    order.id, current, payment_id,
                )
            return False

        _sync_payment_ids(group, orders, payment_id, payment_method)
        for sub in orders:
            if sub.status != OrderStatus.APPROVED:
                _approve_single_order(sub)
        if group is not None:
            group.status = OrderStatus.APPROVED
            group.save(update_fields=['status', 'updated_at'])
        _count_coupon_usage(group.coupon_code if group is not None else orders[0].coupon_code)

        order_id = order.id
        transaction.on_commit(lambda: _send_paid_notifications(order_id))
    return True


def reject_shop_order(order, payment_id: str = '', payment_method: str = '') -> bool:
    """
    Rejeita pedido (e grupo) e libera reservas.
    Não mexe em pedido já aprovado: falha tardia de outra tentativa ou estorno não desfazem a venda.
    """
    with transaction.atomic():
        group, orders = _lock_payment_scope(order)
        group_approved = group is not None and group.status == OrderStatus.APPROVED
        if group_approved or any(o.status == OrderStatus.APPROVED for o in orders):
            return False
        _sync_payment_ids(group, orders, payment_id, payment_method)
        _set_scope_status(group, orders, OrderStatus.REJECTED)
        for sub in orders:
            release_order_reservations(sub.id)
    return True


def mark_payment_pending(order, payment_id: str = '', payment_method: str = '') -> None:
    """Pagamento em andamento (ex.: PIX gerado) — volta o pedido para pendente se ainda não pago."""
    with transaction.atomic():
        group, orders = _lock_payment_scope(order)
        if _is_approved(group, orders):
            return
        _sync_payment_ids(group, orders, payment_id, payment_method)
        _set_scope_status(group, orders, OrderStatus.PENDING)


def apply_mp_payment(order, payment: dict) -> str:
    """Aplica o status de um pagamento do Mercado Pago ao pedido. Retorna o status MP."""
    mp_status = payment.get('status') or ''
    payment_id = str(payment.get('id') or '')
    payment_method = payment.get('payment_method_id') or ''

    if mp_status == 'approved':
        approve_shop_order(order, payment_id, payment_method)
    elif mp_status in MP_FAILED_STATUSES or mp_status in MP_REVERSED_STATUSES:
        rejected = reject_shop_order(order, payment_id, payment_method)
        if not rejected and mp_status in MP_REVERSED_STATUSES:
            logger.error(
                'Pagamento %s do pedido #%s foi %s no Mercado Pago. Pedido segue aprovado: '
                'tratar estoque e repasse do vendedor manualmente (fluxo de devolução).',
                payment_id, order.id, mp_status,
            )
    elif mp_status:
        mark_payment_pending(order, payment_id, payment_method)
    return mp_status
