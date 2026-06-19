"""Saldo e repasses aos vendedores."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from api.models import OrderItem, OrderStatus, PayoutStatus, Seller, SellerPayout, SystemConfig


def credit_seller_earnings_for_order(order) -> None:
    """Credita repasse no saldo do vendedor após pedido aprovado."""
    for item in order.items.select_related('seller').filter(seller__isnull=False):
        if item.seller_balance_credited:
            continue
        amount = item.seller_earning or Decimal('0.00')
        if amount <= 0:
            item.seller_balance_credited = True
            item.save(update_fields=['seller_balance_credited'])
            continue
        Seller.objects.filter(pk=item.seller_id).update(
            balance_available=F('balance_available') + amount,
        )
        item.seller_balance_credited = True
        item.save(update_fields=['seller_balance_credited'])


def debit_seller_for_return(seller_id: int, amount: Decimal) -> None:
    """Debita saldo do vendedor em reembolso aprovado."""
    if amount <= 0:
        return
    Seller.objects.filter(pk=seller_id).update(
        balance_available=F('balance_available') - amount,
    )


@transaction.atomic
def request_payout(seller: Seller, amount: Decimal, pix_key: str) -> SellerPayout:
    config = SystemConfig.get_config()
    minimum = config.minimum_payout_amount or Decimal('50.00')
    amount = Decimal(str(amount)).quantize(Decimal('0.01'))

    if amount < minimum:
        raise ValueError(f'Valor mínimo para saque: R$ {minimum:.2f}')
    if amount > seller.balance_available:
        raise ValueError('Saldo insuficiente.')

    key = (pix_key or seller.pix_key or '').strip()
    if not key:
        raise ValueError('Informe uma chave PIX.')

    seller_locked = Seller.objects.select_for_update().get(pk=seller.pk)
    if amount > seller_locked.balance_available:
        raise ValueError('Saldo insuficiente.')

    Seller.objects.filter(pk=seller.pk).update(
        balance_available=F('balance_available') - amount,
        balance_pending=F('balance_pending') + amount,
    )

    return SellerPayout.objects.create(
        seller=seller,
        amount=amount,
        pix_key=key,
        status=PayoutStatus.PENDING,
    )


@transaction.atomic
def process_payout(payout: SellerPayout, status: str, admin_notes: str = '', payment_reference: str = '') -> SellerPayout:
    payout = SellerPayout.objects.select_for_update().get(pk=payout.pk)
    if payout.status not in (PayoutStatus.PENDING, PayoutStatus.PROCESSING):
        raise ValueError('Repasse já processado.')

    seller = Seller.objects.select_for_update().get(pk=payout.seller_id)

    if status == PayoutStatus.PAID:
        Seller.objects.filter(pk=seller.pk).update(
            balance_pending=F('balance_pending') - payout.amount,
        )
        payout.status = PayoutStatus.PAID
        payout.payment_reference = payment_reference
        payout.processed_at = timezone.now()
    elif status == PayoutStatus.REJECTED:
        Seller.objects.filter(pk=seller.pk).update(
            balance_pending=F('balance_pending') - payout.amount,
            balance_available=F('balance_available') + payout.amount,
        )
        payout.status = PayoutStatus.REJECTED
        payout.processed_at = timezone.now()
    elif status == PayoutStatus.PROCESSING:
        payout.status = PayoutStatus.PROCESSING
    else:
        raise ValueError('Status inválido.')

    payout.admin_notes = admin_notes or payout.admin_notes
    payout.save()
    return payout


def seller_payout_summary(seller: Seller) -> dict:
    pending_payouts = SellerPayout.objects.filter(
        seller=seller,
        status__in=[PayoutStatus.PENDING, PayoutStatus.PROCESSING],
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    return {
        'balance_available': str(seller.balance_available),
        'balance_pending': str(seller.balance_pending),
        'pending_payout_requests': str(pending_payouts),
        'minimum_payout': str(SystemConfig.get_config().minimum_payout_amount or Decimal('50.00')),
        'pix_key': seller.pix_key,
    }
