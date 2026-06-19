"""Notificações in-app, e-mail e WhatsApp."""
from __future__ import annotations

import logging
import threading
from urllib.parse import quote

from django.conf import settings

from api.models import NotificationType, UserNotification, SystemConfig
from api.views.contact_views import normalize_whatsapp_phone, build_whatsapp_url

logger = logging.getLogger(__name__)


def _frontend_url(path: str = '/') -> str:
    base = getattr(settings, 'FRONTEND_URL', 'http://127.0.0.1:5173').rstrip('/')
    path = path if path.startswith('/') else f'/{path}'
    return f'{base}{path}'


def create_notification(
    user,
    notification_type: str,
    title: str,
    body: str = '',
    link: str = '',
    metadata: dict | None = None,
    send_email: bool = True,
    send_whatsapp: bool = True,
) -> UserNotification:
    notif = UserNotification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        link=link or '',
        metadata=metadata or {},
    )

    if send_email or send_whatsapp:
        threading.Thread(
            target=_dispatch_external,
            args=(user, title, body, link, send_email, send_whatsapp),
            daemon=True,
        ).start()
    return notif


def _dispatch_external(user, title, body, link, send_email, send_whatsapp):
    full_link = link
    if link and link.startswith('/'):
        full_link = _frontend_url(link)

    if send_email:
        try:
            from api.services.email_service import email_service
            email_service.send_notification_email(
                user.email, user.name, title, body, full_link,
            )
        except Exception as exc:
            logger.warning('Falha email notificação: %s', exc)

    if send_whatsapp:
        phone = (user.phone or '').strip()
        if not phone:
            return
        try:
            msg = f'*Galelugi Peças*\n{title}'
            if body:
                msg += f'\n{body}'
            if full_link:
                msg += f'\n{full_link}'
            url = build_whatsapp_url(normalize_whatsapp_phone(phone), msg)
            logger.info('WhatsApp notification link for %s: %s', user.email, url[:80])
        except Exception as exc:
            logger.warning('Falha WhatsApp notificação: %s', exc)


def notify_seller_new_order(seller, order, item_count: int):
    user = seller.user
    create_notification(
        user,
        NotificationType.SELLER_NEW_ORDER,
        f'Nova venda — pedido #{order.id}',
        f'{item_count} item(ns) para enviar. Total do pedido: R$ {order.amount:.2f}',
        link='/vender/',
        metadata={'order_id': order.id},
    )


def notify_buyer_order_paid(order):
    create_notification(
        order.user,
        NotificationType.ORDER_PAID,
        f'Pagamento confirmado — pedido #{order.id}',
        f'Seu pedido de R$ {order.amount:.2f} foi aprovado.',
        link='/pedidos/',
        metadata={'order_id': order.id},
    )


def notify_buyer_shipped(order, tracking_code: str = ''):
    body = f'Seu pedido #{order.id} foi enviado.'
    if tracking_code:
        body += f' Rastreio: {tracking_code}'
    create_notification(
        order.user,
        NotificationType.ORDER_SHIPPED,
        f'Pedido #{order.id} enviado',
        body,
        link='/pedidos/',
        metadata={'order_id': order.id, 'tracking_code': tracking_code},
    )


def notify_chat_message(recipient, product_name: str, sender_name: str):
    create_notification(
        recipient,
        NotificationType.CHAT_MESSAGE,
        f'Nova mensagem sobre {product_name}',
        f'{sender_name} enviou uma mensagem.',
        link='/vender/',
    )


def notify_return_opened(seller_user, return_request):
    create_notification(
        seller_user,
        NotificationType.RETURN_OPENED,
        f'Devolução aberta — pedido #{return_request.order_id}',
        return_request.reason,
        link='/vender/',
        metadata={'return_id': return_request.id},
    )


def notify_return_approved(buyer, return_request):
    create_notification(
        buyer,
        NotificationType.RETURN_APPROVED,
        f'Devolução aprovada — pedido #{return_request.order_id}',
        'Siga as instruções para envio do item.',
        link='/pedidos/',
        metadata={'return_id': return_request.id},
    )


def notify_payout_paid(seller, payout):
    create_notification(
        seller.user,
        NotificationType.PAYOUT_PAID,
        f'Saque de R$ {payout.amount:.2f} pago',
        f'Repasse enviado para PIX {payout.pix_key}',
        link='/vender/',
        metadata={'payout_id': payout.id},
    )


def notify_invoice_issued(user, invoice_request):
    create_notification(
        user,
        NotificationType.INVOICE_ISSUED,
        f'NF-e emitida — pedido #{invoice_request.order_id}',
        f'Nota {invoice_request.invoice_number or ""}'.strip(),
        link='/pedidos/',
        metadata={'invoice_id': invoice_request.id},
    )
