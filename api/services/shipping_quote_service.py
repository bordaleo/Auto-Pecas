"""Cotação de frete multi-loja (agrupa por vendedor)."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from api.models import Product, SystemConfig
from api.services.melhor_envio_service import calculate_shipping_with_provider
from api.services.shipping_origin import resolve_shipping_origin, store_label_for_seller
from api.services.shipping_service import get_pickup_address


def _seller_key(seller) -> str:
    return str(seller.id) if seller else 'platform'


def _me_cart_items(group_items: list[dict]) -> list[dict]:
    return [
        {
            'price': float(i['unit_price']),
            'quantity': i['quantity'],
            'weight_kg': float(i.get('weight_kg') or 1),
            'width_cm': i.get('width_cm') or 20,
            'height_cm': i.get('height_cm') or 10,
            'length_cm': i.get('length_cm') or 30,
        }
        for i in group_items
    ]


def group_cart_by_seller(cart_items: list[dict]) -> dict[str, list[dict]]:
    """
    Agrupa itens do carrinho por vendedor.
    cart_items: [{product_id, quantity, price?, weight_kg?, ...}]
    """
    product_ids = [int(i['product_id']) for i in cart_items if i.get('product_id')]
    if not product_ids:
        return {}

    products = Product.objects.select_related('seller').filter(id__in=product_ids, is_active=True)
    pmap = {p.id: p for p in products}

    groups: dict[str, list[dict]] = defaultdict(list)
    for item in cart_items:
        pid = int(item.get('product_id') or 0)
        product = pmap.get(pid)
        if not product:
            continue
        groups[_seller_key(product.seller)].append({
            'product': product,
            'seller': product.seller,
            'quantity': int(item.get('quantity') or 1),
            'unit_price': Decimal(str(item.get('price') or product.price)),
            'weight_kg': item.get('weight_kg') if item.get('weight_kg') is not None else product.weight_kg,
            'width_cm': item.get('width_cm') if item.get('width_cm') is not None else product.width_cm,
            'height_cm': item.get('height_cm') if item.get('height_cm') is not None else product.height_cm,
            'length_cm': item.get('length_cm') if item.get('length_cm') is not None else product.length_cm,
        })
    return groups


def quote_cart_shipping(
    delivery_method: str,
    zip_code: str,
    cart_items: list[dict],
    subtotal: Decimal | None = None,
) -> tuple[Decimal | None, list[dict], str, bool]:
    """
    Cota frete por loja.
    Retorna (total_fee, breakdown, pickup_address, needs_zip).
    """
    config = SystemConfig.get_config()
    pickup = get_pickup_address()
    groups = group_cart_by_seller(cart_items)

    if not groups:
        fee, is_free, _, meta = calculate_shipping_with_provider(
            delivery_method,
            subtotal or Decimal('0'),
            zip_code,
            cart_items=cart_items or None,
        )
        if fee is None:
            return None, [], pickup, True
        return fee, [], pickup, False

    breakdown = []
    total_fee = Decimal('0.00')

    for key, items in groups.items():
        seller = items[0]['seller']
        group_sub = sum(i['unit_price'] * i['quantity'] for i in items)
        origin_zip, store_name, ships_from_platform = resolve_shipping_origin(seller)

        fee, is_free, _, meta = calculate_shipping_with_provider(
            delivery_method,
            group_sub,
            zip_code,
            cart_items=_me_cart_items(items),
            origin_zip=origin_zip,
        )
        if fee is None:
            return None, [], pickup, True

        total_fee += fee
        breakdown.append({
            'seller_key': key,
            'seller_id': seller.id if seller else None,
            'seller_slug': seller.slug if seller else '',
            'store_name': store_name,
            'is_official': bool(seller.is_official) if seller else True,
            'ships_from_platform': ships_from_platform,
            'subtotal': str(group_sub.quantize(Decimal('0.01'))),
            'shipping_fee': str(fee.quantize(Decimal('0.01'))),
            'is_free': is_free,
            'shipping_service_name': meta.get('service_name', ''),
            'shipping_days': meta.get('days'),
            'shipping_provider': meta.get('provider', 'fixed'),
        })

    return total_fee.quantize(Decimal('0.01')), breakdown, pickup, False


def quote_legacy_cart_shipping(
    delivery_method: str,
    zip_code: str,
    subtotal: Decimal,
    cart_items: list[dict] | None,
) -> tuple[Decimal | None, list[dict], str, bool]:
    """Fallback quando itens não têm product_id (cotação única)."""
    pickup = get_pickup_address()
    fee, _, _, meta = calculate_shipping_with_provider(
        delivery_method, subtotal, zip_code, cart_items=cart_items,
    )
    if fee is None:
        return None, [], pickup, True
    return fee, [{
        'seller_key': 'platform',
        'seller_id': None,
        'seller_slug': '',
        'store_name': store_label_for_seller(None),
        'is_official': True,
        'ships_from_platform': True,
        'subtotal': str(subtotal),
        'shipping_fee': str(fee),
        'is_free': fee == 0,
        'shipping_service_name': meta.get('service_name', ''),
        'shipping_days': meta.get('days'),
        'shipping_provider': meta.get('provider', 'fixed'),
    }], pickup, False
