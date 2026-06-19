from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from api.models import AbandonedCart


def sync_abandoned_cart(user, email, items):
    """Salva ou atualiza snapshot do carrinho."""
    email = (email or '').strip().lower()
    if not email or not items:
        return None

    subtotal = sum(
        Decimal(str(i.get('price', 0))) * int(i.get('quantity', 1))
        for i in items
    )
    subtotal = subtotal.quantize(Decimal('0.01'))

    cart, _ = AbandonedCart.objects.update_or_create(
        email=email,
        defaults={
            'user': user if user and user.is_authenticated else None,
            'items': items,
            'subtotal': subtotal,
            'recovered_at': None,
        },
    )
    return cart


def mark_cart_recovered(email):
    email = (email or '').strip().lower()
    if not email:
        return
    AbandonedCart.objects.filter(email=email, recovered_at__isnull=True).update(
        recovered_at=timezone.now(),
    )


def get_carts_pending_reminder(hours=1):
    """Carrinhos sem lembrete há mais de N horas."""
    cutoff = timezone.now() - timedelta(hours=hours)
    return AbandonedCart.objects.filter(
        reminder_sent_at__isnull=True,
        recovered_at__isnull=True,
        subtotal__gt=0,
        updated_at__lte=cutoff,
    ).select_related('user')
