import logging
import os
import threading

from django.conf import settings

from services.email_service import send_email

logger = logging.getLogger(__name__)

STORE = "Galelugi Peças"
ACCENT = "#e85d04"


def _wrap(title: str, body: str) -> str:
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;font-family:Arial,sans-serif;background:#f4f4f5;">
<div style="max-width:560px;margin:24px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">
<div style="background:#0f172a;color:#fff;padding:24px;">
<h1 style="margin:0;font-size:20px;">{STORE}</h1>
<p style="margin:6px 0 0;opacity:.85;font-size:14px;">{title}</p>
</div>
<div style="padding:28px;color:#334155;line-height:1.6;">{body}</div>
<div style="padding:16px 28px;background:#f8fafc;font-size:12px;color:#64748b;">
Equipe {STORE} · Email automático, não responda.
</div></div></body></html>"""


def _code_block(code: str) -> str:
    return (
        f'<div style="text-align:center;font-size:32px;letter-spacing:10px;font-weight:700;'
        f'padding:16px;background:#f1f5f9;border-radius:8px;margin:20px 0;color:#0f172a;">{code}</div>'
    )


class EmailService:
    def __init__(self):
        self.from_email = os.getenv("SMTP_FROM_EMAIL") or getattr(
            settings, "DEFAULT_FROM_EMAIL", "suporte.amorlize@gmail.com"
        )
        self.enabled = bool(os.getenv("BREVO_API_KEY") and self.from_email)

    def send_password_reset_email(self, to_email: str, reset_code: str, user_name: str) -> bool:
        if not self.enabled:
            return False
        body = (
            f"<p>Olá, <strong>{user_name}</strong>!</p>"
            f"<p>Use o código abaixo para redefinir sua senha:</p>{_code_block(reset_code)}"
            f"<p><strong>Válido por 24 horas.</strong> Se não foi você, ignore este email.</p>"
        )
        return send_email(to_email, f"Recuperação de senha — {STORE}", _wrap("Recuperação de senha", body))

    def _send_verification_email_sync(self, to_email: str, verification_code: str, user_name: str) -> bool:
        body = (
            f"<p>Olá, <strong>{user_name}</strong>!</p>"
            f"<p>Confirme seu cadastro com o código:</p>{_code_block(verification_code)}"
            f"<p><strong>Válido por 24 horas.</strong></p>"
        )
        return send_email(to_email, f"Verifique sua conta — {STORE}", _wrap("Verificação de conta", body))

    def send_verification_email(self, to_email: str, verification_code: str, user_name: str, async_send: bool = True) -> bool:
        if not self.enabled:
            return False
        if async_send:
            threading.Thread(
                target=self._send_verification_email_sync,
                args=(to_email, verification_code, user_name),
                daemon=True,
            ).start()
            return True
        return self._send_verification_email_sync(to_email, verification_code, user_name)

    def send_email_change_email(self, to_email: str, verification_code: str, user_name: str, new_email: str) -> bool:
        if not self.enabled:
            return False
        body = (
            f"<p>Olá, <strong>{user_name}</strong>!</p>"
            f"<p>Confirme a alteração do email para <strong>{new_email}</strong>:</p>"
            f"{_code_block(verification_code)}"
        )
        return send_email(new_email, f"Confirme seu novo email — {STORE}", _wrap("Mudança de email", body))

    def send_order_confirmation(self, order) -> bool:
        to_email = (order.order_email or order.user.email or "").strip()
        if not to_email or not self.enabled:
            return False
        frontend = getattr(settings, "FRONTEND_URL", "http://127.0.0.1:8000").rstrip("/")
        rows = ""
        for item in order.items.all():
            rows += (
                f"<tr><td style='padding:8px;border-bottom:1px solid #e2e8f0;'>{item.product_name}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #e2e8f0;text-align:center;'>{item.quantity}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #e2e8f0;text-align:right;'>R$ {item.subtotal:.2f}</td></tr>"
            )
        body = (
            f"<p>Olá, <strong>{order.customer_name or order.user.name}</strong>!</p>"
            f"<p>Pagamento confirmado — pedido <strong>#{order.id}</strong>.</p>"
            f"<table style='width:100%;border-collapse:collapse;margin:16px 0;'>"
            f"<thead><tr style='background:#f1f5f9;'>"
            f"<th style='padding:8px;text-align:left;'>Peça</th>"
            f"<th style='padding:8px;'>Qtd</th><th style='padding:8px;text-align:right;'>Subtotal</th>"
            f"</tr></thead><tbody>{rows}</tbody></table>"
            f"<p style='text-align:right;font-size:18px;font-weight:700;'>Total: R$ {order.amount:.2f}</p>"
            f"<p style='text-align:center;margin-top:24px;'>"
            f"<a href='{frontend}/pedidos/' style='background:{ACCENT};color:#fff;padding:12px 28px;"
            f"text-decoration:none;border-radius:8px;font-weight:700;'>Ver meus pedidos</a></p>"
        )
        return send_email(to_email, f"Pedido #{order.id} confirmado — {STORE}", _wrap("Pedido confirmado", body))

    def send_abandoned_cart_email(self, cart) -> bool:
        to_email = (cart.email or "").strip()
        if not to_email or not self.enabled or not cart.items:
            return False
        frontend = getattr(settings, "FRONTEND_URL", "http://127.0.0.1:3000").rstrip("/")
        rows = ""
        for item in cart.items[:6]:
            name = item.get("name", "Peça")
            qty = item.get("quantity", 1)
            price = float(item.get("price", 0)) * qty
            rows += (
                f"<li style='margin:6px 0;'>{qty}x {name} — "
                f"<strong>R$ {price:.2f}</strong></li>"
            )
        body = (
            f"<p>Olá!</p>"
            f"<p>Você deixou peças no carrinho da <strong>{STORE}</strong>. "
            f"Elas ainda estão reservadas para você:</p>"
            f"<ul style='padding-left:20px;'>{rows}</ul>"
            f"<p style='font-size:18px;font-weight:700;'>Subtotal: R$ {cart.subtotal:.2f}</p>"
            f"<p style='text-align:center;margin-top:24px;'>"
            f"<a href='{frontend}/carrinho/' style='background:{ACCENT};color:#fff;padding:12px 28px;"
            f"text-decoration:none;border-radius:8px;font-weight:700;'>Voltar ao carrinho</a></p>"
            f"<p style='font-size:13px;color:#64748b;margin-top:16px;'>"
            f"Use o cupom <strong>BEMVINDO10</strong> na primeira compra.</p>"
        )
        return send_email(
            to_email,
            f"Seu carrinho está esperando — {STORE}",
            _wrap("Carrinho abandonado", body),
        )


email_service = EmailService()
