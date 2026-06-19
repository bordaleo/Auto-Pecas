"""Cotação de frete via Melhor Envio (com fallback para tabela fixa)."""
from __future__ import annotations

import logging
import re
from decimal import Decimal

import requests
from django.conf import settings

from api.models import DeliveryMethod, SystemConfig
from api.services.shipping_service import calculate_shipping_fee as fixed_shipping_fee, get_pickup_address, normalize_zip

logger = logging.getLogger(__name__)

ME_BASE = 'https://sandbox.melhorenvio.com.br/api/v2'
ME_BASE_PROD = 'https://melhorenvio.com.br/api/v2'


def _api_base(sandbox: bool) -> str:
    return ME_BASE if sandbox else ME_BASE_PROD


def _origin_zip() -> str:
    config = SystemConfig.get_config()
    digits = normalize_zip(config.origin_zip or '01310100')
    return digits or '01310100'


def quote_melhor_envio(destination_zip: str, cart_items: list[dict]) -> dict | None:
    """
    Cota frete no Melhor Envio.
    cart_items: [{price, quantity, weight_kg, width_cm, height_cm, length_cm}, ...]
    Retorna {fee, service_name, days, provider} ou None se indisponível.
    """
    config = SystemConfig.get_config()
    token = (config.melhor_envio_token or getattr(settings, 'MELHOR_ENVIO_TOKEN', '') or '').strip()
    if not token:
        return None

    dest = normalize_zip(destination_zip)
    if len(dest) != 8:
        return None

    products = []
    for i, item in enumerate(cart_items):
        qty = int(item.get('quantity') or 1)
        price = float(item.get('price') or 0)
        products.append({
            'id': str(i + 1),
            'width': int(item.get('width_cm') or 20),
            'height': int(item.get('height_cm') or 10),
            'length': int(item.get('length_cm') or 30),
            'weight': float(item.get('weight_kg') or 1),
            'insurance_value': price,
            'quantity': qty,
        })

    payload = {
        'from': {'postal_code': _origin_zip()},
        'to': {'postal_code': dest},
        'products': products,
    }

    url = f"{_api_base(config.melhor_envio_sandbox)}/me/shipment/calculate"
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Galelugi Pecas (contato@galelugi.com.br)',
            },
            timeout=12,
        )
        if resp.status_code != 200:
            logger.warning('Melhor Envio HTTP %s: %s', resp.status_code, resp.text[:300])
            return None
        options = resp.json()
        if not isinstance(options, list) or not options:
            return None
        best = min(options, key=lambda o: float(o.get('price') or o.get('custom_price') or 999999))
        fee = Decimal(str(best.get('price') or best.get('custom_price') or '0')).quantize(Decimal('0.01'))
        service = best.get('name') or best.get('company', {}).get('name') or 'Melhor Envio'
        days = best.get('delivery_time') or best.get('delivery_range', {}).get('max') or None
        return {
            'fee': fee,
            'service_name': str(service)[:80],
            'days': int(days) if days else None,
            'provider': 'melhor_envio',
        }
    except Exception as exc:
        logger.warning('Melhor Envio indisponível: %s', exc)
        return None


def calculate_shipping_with_provider(
    delivery_method,
    subtotal,
    zip_code=None,
    cart_items: list[dict] | None = None,
):
    """
    Calcula frete: Melhor Envio se configurado, senão tabela fixa.
    Retorna (fee, is_free, pickup_address, meta_dict).
    """
    subtotal = Decimal(str(subtotal or '0'))
    config = SystemConfig.get_config()
    free_min = config.free_shipping_min or Decimal('299.00')
    pickup = get_pickup_address()

    if delivery_method == DeliveryMethod.PICKUP:
        return Decimal('0.00'), True, pickup, {'provider': 'pickup', 'service_name': 'Retirada na loja'}

    if subtotal >= free_min:
        return Decimal('0.00'), True, pickup, {'provider': 'free', 'service_name': 'Frete grátis'}

    if cart_items:
        me = quote_melhor_envio(zip_code or '', cart_items)
        if me and me['fee'] is not None:
            return me['fee'], False, pickup, me

    fee, is_free, addr = fixed_shipping_fee(delivery_method, subtotal, zip_code)
    if fee is None:
        return None, False, pickup, {'provider': 'fixed', 'service_name': ''}
    return fee, is_free, addr, {'provider': 'fixed', 'service_name': 'Entrega padrão'}
