from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from django.conf import settings
from mercadopago import SDK

logger = logging.getLogger(__name__)

_MP_PAYER_FAULT_CODES = frozenset({
    "cc_rejected_bad_filled_card_number", "cc_rejected_bad_filled_date",
    "cc_rejected_bad_filled_security_code", "cc_rejected_blacklist",
    "cc_rejected_call_for_authorize", "cc_rejected_card_disabled",
    "cc_rejected_duplicated_payment", "cc_rejected_high_risk",
    "cc_rejected_insufficient_amount", "cc_rejected_invalid_installments",
    "cc_rejected_max_attempts", "cc_rejected_other_reason",
    "cc_rejected_card_type_not_allowed", "rejected_by_bank", "insufficient_amount",
})


def _mp_create_response_is_payer_fault(response: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(response, dict):
        return False
    body = response.get("response")
    if not isinstance(body, dict):
        return False
    causes = body.get("cause")
    if not isinstance(causes, list) or not causes:
        msg = (body.get("message") or "").lower()
        return "rejected" in msg or "fund" in msg
    for item in causes:
        if not isinstance(item, dict):
            return False
        code = item.get("code") or ""
        if code in _MP_PAYER_FAULT_CODES or (isinstance(code, str) and code.startswith("cc_rejected")):
            continue
        return False
    return True


class PaymentService:
    def __init__(self):
        self.access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None)
        self.enabled = bool(self.access_token)
        self._last_payment_create_response: Optional[Dict[str, Any]] = None
        if self.enabled:
            self.sdk = SDK(self.access_token)
        else:
            self.sdk = None
            logger.warning("Mercado Pago não configurado.")

    def create_shop_payment_preference(
        self,
        items: list,
        amount: Decimal,
        user_id: int,
        user_name: str,
        user_email: str,
        external_reference: str,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        try:
            frontend_url = (getattr(settings, 'FRONTEND_URL', 'http://localhost:8000') or 'http://localhost:8000').rstrip('/')
            backend_url = (getattr(settings, 'BACKEND_URL', 'http://localhost:8000') or 'http://localhost:8000').rstrip('/')

            mp_items = [{
                "title": (item.get('title') or 'Peça automotiva')[:256],
                "quantity": int(item.get('quantity') or 1),
                "unit_price": float(item.get('unit_price') or 0),
                "currency_id": "BRL",
            } for item in items]

            if not mp_items:
                mp_items = [{
                    "title": "Galelugi Peças — Pedido",
                    "quantity": 1,
                    "unit_price": float(amount),
                    "currency_id": "BRL",
                }]
            else:
                items_total = round(sum(i["quantity"] * i["unit_price"] for i in mp_items), 2)
                target = round(float(amount), 2)
                diff = round(target - items_total, 2)
                if diff != 0:
                    mp_items.append({
                        "title": "Ajuste",
                        "quantity": 1,
                        "unit_price": diff,
                        "currency_id": "BRL",
                    })

            preference_data = {
                "items": mp_items,
                "payer": {"name": user_name, "email": user_email},
                "back_urls": {
                    "success": f"{frontend_url}/pedidos/",
                    "failure": f"{frontend_url}/pedidos/",
                    "pending": f"{frontend_url}/pedidos/",
                },
                "external_reference": external_reference,
                "notification_url": f"{backend_url}/api/v1/payments/webhook",
                "statement_descriptor": "GALELUGI",
                "payment_methods": {
                    "excluded_payment_methods": [{"id": "consumer_credits"}],
                    "installments": 12,
                },
            }
            # auto_return só com URLs HTTPS (produção); em localhost HTTP o MP rejeita
            if frontend_url.startswith("https://"):
                preference_data["auto_return"] = "approved"
            response = self.sdk.preference().create(preference_data)
            if isinstance(response, dict) and response.get("status") in [200, 201]:
                data = response.get("response", {})
                if data.get("id"):
                    return data
            logger.error("Erro ao criar preferência MP: %s", response)
            return None
        except Exception as e:
            logger.exception("Exceção ao criar preferência MP: %s", e)
            return None

    def get_payment(self, payment_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        try:
            response = self.sdk.payment().get(payment_id)
            if isinstance(response, dict) and response.get("status") in [200, 201]:
                return response.get("response")
            return None
        except Exception as e:
            logger.error("Erro ao buscar pagamento %s: %s", payment_id, e)
            return None

    def create_payment(self, payment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._last_payment_create_response = None
        if not self.enabled:
            return None
        try:
            response = self.sdk.payment().create(payment_data)
            if isinstance(response, dict):
                self._last_payment_create_response = response
            if isinstance(response, dict) and response.get("status") in [200, 201]:
                data = response.get("response", {})
                if isinstance(data, dict):
                    return data
            return None
        except Exception as e:
            logger.exception("Erro ao criar pagamento MP: %s", e)
            return None

    def last_payment_create_was_incomplete_or_abandoned(self) -> bool:
        response = self._last_payment_create_response
        if not isinstance(response, dict):
            return False
        if response.get("status") in (200, 201):
            return False
        if _mp_create_response_is_payer_fault(response):
            return False
        return True

    def search_payments(self, external_reference: str, limit: int = 5) -> list[Dict[str, Any]]:
        if not self.enabled:
            return []
        try:
            payload = {
                "sort": "date_created",
                "criteria": "desc",
                "limit": limit,
                "external_reference": external_reference,
            }
            response = self.sdk.payment().search(payload)
            if isinstance(response, dict) and response.get("status") in [200, 201]:
                data = response.get("response", {})
                results = data.get("results", []) if isinstance(data, dict) else []
                return results if isinstance(results, list) else []
            return []
        except Exception as e:
            logger.error("Erro ao buscar pagamentos: %s", e)
            return []


payment_service = PaymentService()
