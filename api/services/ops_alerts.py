"""
Alertas operacionais (produção): webhook Discord/Slack/genérico e e-mail opcional.

Variáveis de ambiente:
  OPS_ALERT_WEBHOOK_URL — URL do webhook (Discord, Slack ou API que aceite JSON).
  OPS_ALERT_EMAIL — e-mail para receber cópia dos alertas (usa SMTP já configurado).
  OPS_ALERT_DEBOUNCE_SEC — intervalo mínimo entre alertas com a mesma chave (default 120).
    A chave inclui categoria + mensagem + campos de escopo em ``extra`` (order_id, video_id,
    user_id, token, slug, path). Assim o mesmo texto para outro pedido não é suprimido.
  OPS_ALERT_IN_DEBUG — se true, envia alertas mesmo com DEBUG=True (default false).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import traceback
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_last_sent: Dict[str, float] = {}

# Incluídos na chave de debounce quando presentes em ``extra`` (evita fundir falhas de pedidos diferentes).
_DEBOUNCE_SCOPE_KEYS = ("order_id", "video_id", "user_id", "token", "slug", "path")


def _debounce_scope_fragment(extra: Optional[Dict[str, Any]]) -> str:
    if not extra:
        return ""
    parts = []
    for k in _DEBOUNCE_SCOPE_KEYS:
        v = extra.get(k)
        if v is not None and v != "":
            parts.append(f"{k}={v}")
    return "|".join(parts)


def _debounce_key(category: str, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
    scope = _debounce_scope_fragment(extra)
    raw = f"{category}|{message[:400]}|{scope}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:24]


def scope_extra_from_log_record(record: logging.LogRecord) -> Optional[Dict[str, Any]]:
    """Extrai campos de escopo do LogRecord (via logger.error(..., extra={...}))."""
    found: Dict[str, Any] = {}
    for k in _DEBOUNCE_SCOPE_KEYS:
        if hasattr(record, k):
            v = getattr(record, k, None)
            if v is not None and v != "":
                found[k] = v
    return found or None


def _should_skip(key: str) -> bool:
    try:
        debounce = int(os.getenv("OPS_ALERT_DEBOUNCE_SEC", "120"))
    except ValueError:
        debounce = 120
    now = time.time()
    last = _last_sent.get(key, 0.0)
    if now - last < debounce:
        return True
    _last_sent[key] = now
    if len(_last_sent) > 500:
        for k in list(_last_sent.keys())[:200]:
            _last_sent.pop(k, None)
    return False


def _ops_enabled() -> bool:
    from django.conf import settings

    if getattr(settings, "DEBUG", False) and not getattr(settings, "OPS_ALERT_IN_DEBUG", False):
        return False
    return bool(
        getattr(settings, "OPS_ALERT_WEBHOOK_URL", None)
        or getattr(settings, "OPS_ALERT_EMAIL", None)
    )


def send_ops_alert(
    category: str,
    message: str,
    *,
    detail: Optional[str] = None,
    exc: Optional[BaseException] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Envia alerta (webhook + e-mail opcional). Silencioso se nada configurado ou em DEBUG local.
    """
    try:
        from django.conf import settings
    except Exception:
        return

    if getattr(settings, "DEBUG", False) and not getattr(settings, "OPS_ALERT_IN_DEBUG", False):
        return

    if not (
        getattr(settings, "OPS_ALERT_WEBHOOK_URL", None)
        or getattr(settings, "OPS_ALERT_EMAIL", None)
    ):
        return

    parts = [f"[{category}] {message}"]
    if detail:
        parts.append(detail[:3500])
    if exc is not None:
        parts.append(f"{type(exc).__name__}: {exc}")
        parts.append(traceback.format_exc()[-6000:])
    if extra:
        try:
            parts.append(json.dumps(extra, ensure_ascii=False, default=str)[:2000])
        except Exception:
            pass
    body_text = "\n\n".join(parts)
    body_text = body_text[:12000]

    key = _debounce_key(category, message, extra)
    if _should_skip(key):
        logger.debug("Ops alert debounced: %s", category)
        return

    _persist_ops_alert_event(category, message, detail, extra, body_text)

    webhook_url = (getattr(settings, "OPS_ALERT_WEBHOOK_URL", None) or "").strip()
    if webhook_url:
        _post_webhook(webhook_url, category, body_text)

    email_to = (getattr(settings, "OPS_ALERT_EMAIL", None) or "").strip()
    if email_to:
        _send_alert_email(settings, email_to, category, body_text)


def _persist_ops_alert_event(
    category: str,
    message: str,
    detail: Optional[str],
    extra: Optional[Dict[str, Any]],
    body_text: str,
) -> None:
    """Grava cópia local para o painel /painel/erros/ (melhor esforço)."""
    try:
        from api.models import OpsAlertEvent

        OpsAlertEvent.objects.create(
            category=(category or "")[:200],
            message=(message or "")[:8000],
            detail=(detail or "")[:12000],
            body_excerpt=(body_text or "")[:8000],
            extra=extra,
        )
        n = OpsAlertEvent.objects.count()
        if n > 2500:
            old_ids = list(
                OpsAlertEvent.objects.order_by("created_at").values_list("id", flat=True)[: max(1, n - 2000)]
            )
            if old_ids:
                OpsAlertEvent.objects.filter(pk__in=old_ids).delete()
    except Exception as e:
        logger.warning("OpsAlertEvent persist falhou: %s", e)


def _post_webhook(url: str, category: str, text: str) -> None:
    """Discord (embed), Slack (text) ou JSON genérico."""
    low = url.lower()
    try:
        if "discord.com/api/webhooks" in low:
            payload = {
                "embeds": [
                    {
                        "title": f"Amorlize — {category}",
                        "description": text[:4000],
                        "color": 15158332,
                    }
                ]
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "AmorlizeOps/1.0"},
                method="POST",
            )
        elif "hooks.slack.com" in low:
            payload = {"text": f"*{category}*\n{text[:12000]}"}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "AmorlizeOps/1.0"},
                method="POST",
            )
        else:
            payload = {"source": "amorlize", "category": category, "text": text[:12000]}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "User-Agent": "AmorlizeOps/1.0"},
                method="POST",
            )
        with urllib.request.urlopen(req, timeout=12) as resp:
            resp.read()
    except urllib.error.HTTPError as e:
        logger.warning("Ops webhook HTTP %s: %s", e.code, e.read()[:300] if e.fp else "")
    except Exception as e:
        logger.warning("Ops webhook falhou: %s", e)


def _send_alert_email(settings: Any, to_email: str, category: str, text: str) -> None:
    try:
        from django.core.mail import send_mail

        subject = f"[Amorlize] Alerta: {category}"
        send_mail(
            subject,
            text[:100000],
            getattr(settings, "DEFAULT_FROM_EMAIL", None),
            [to_email],
            fail_silently=True,
        )
    except Exception as e:
        logger.warning("Ops alert e-mail falhou: %s", e)


def alert_from_log_record(record: logging.LogRecord) -> None:
    """Usado pelo logging handler."""
    if getattr(record, "skip_ops_alert", False):
        return
    try:
        msg = record.getMessage()
    except Exception:
        msg = str(record.msg)
    detail = None
    if record.exc_info:
        detail = "".join(traceback.format_exception_only(record.exc_info[1]))[-2000:]
    scope = scope_extra_from_log_record(record)
    send_ops_alert(
        category=f"log:{record.levelname}",
        message=msg[:800],
        detail=detail,
        extra=scope,
    )


def alert_unhandled_request_exception(request: Any, exception: BaseException) -> None:
    """Middleware: falha não tratada na view."""
    path = getattr(request, "path", "?")
    method = getattr(request, "method", "?")
    send_ops_alert(
        category="request_500",
        message=f"{method} {path}",
        exc=exception,
        extra={"path": path, "method": method},
    )
