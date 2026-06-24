"""Resolve CEP e rótulo de origem do frete por vendedor."""

from __future__ import annotations

from api.models import Seller, SystemConfig
from api.services.shipping_service import normalize_zip


def platform_origin_zip() -> str:
    config = SystemConfig.get_config()
    digits = normalize_zip(config.origin_zip or '01310100')
    return digits or '01310100'


def platform_store_name() -> str:
    config = SystemConfig.get_config()
    return (config.store_name or 'Galelugi Peças').strip()


def resolve_shipping_origin(seller: Seller | None) -> tuple[str, str, bool]:
    """
    Retorna (origin_zip, store_name, ships_from_platform).
  ships_from_platform=True quando o envio sai do endereço da plataforma/Sandroni.
    """
    if seller is None:
        return platform_origin_zip(), platform_store_name(), True

    if seller.ships_from_platform:
        return platform_origin_zip(), platform_store_name(), True

    seller_zip = normalize_zip(seller.origin_zip or '')
    if len(seller_zip) == 8:
        return seller_zip, seller.store_name, False

    return platform_origin_zip(), seller.store_name, True


def store_label_for_seller(seller: Seller | None) -> str:
    if seller:
        return seller.store_name
    return platform_store_name()
