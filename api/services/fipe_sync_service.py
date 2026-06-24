"""Sincroniza marcas e modelos de carros via API FIPE (Parallelum)."""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.request
from datetime import date

from django.utils.text import slugify

from api.models import VehicleBrand, VehicleModel

logger = logging.getLogger(__name__)

FIPE_BASE = 'https://parallelum.com.br/fipe/api/v1/carros'

BRAND_NAME_MAP = {
    'VW - VolksWagen': 'Volkswagen',
    'GM - Chevrolet': 'Chevrolet',
    'Hyundai': 'Hyundai',
    'Toyota': 'Toyota',
    'Honda': 'Honda',
    'Renault': 'Renault',
    'Nissan': 'Nissan',
    'Jeep': 'Jeep',
    'BMW': 'BMW',
    'Mercedes-Benz': 'Mercedes-Benz',
    'Audi': 'Audi',
    'Peugeot': 'Peugeot',
    'Citroën': 'Citroen',
    'Citroen': 'Citroen',
    'Mitsubishi': 'Mitsubishi',
    'Kia Motors': 'Kia',
    'Kia': 'Kia',
    'Land Rover': 'Land Rover',
    'Volvo': 'Volvo',
    'Porsche': 'Porsche',
    'Mini': 'Mini',
    'Chery': 'Chery',
    'JAC': 'JAC',
    'RAM': 'RAM',
    'Fiat': 'Fiat',
    'Ford': 'Ford',
}


def _fetch_json(url: str) -> list | dict | None:
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Galelugi-Pecas/1.0', 'Accept': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8', errors='replace'))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        logger.warning('FIPE fetch failed %s: %s', url, exc)
        return None


def _canonical_brand(name: str) -> str:
    clean = (name or '').strip()
    if clean in BRAND_NAME_MAP:
        return BRAND_NAME_MAP[clean]
    for key, val in BRAND_NAME_MAP.items():
        if key.lower() in clean.lower() or clean.lower() in key.lower():
            return val
    if ' - ' in clean:
        return clean.split(' - ', 1)[-1].strip()
    return clean


def _base_model_name(fipe_name: str) -> str:
    """Extrai nome base do modelo FIPE (ex.: 'Gol 1.0' -> 'Gol')."""
    name = (fipe_name or '').strip()
    name = re.sub(r'\s+\d[\d,.]*.*$', '', name)
    name = re.sub(r'\s+(Flex|Gasolina|Diesel|Híbrido|Hibrido|Elétrico|Eletrico).*$', '', name, flags=re.I)
    name = name.strip(' -/')
    if not name:
        return fipe_name.strip()
    return name[:1].upper() + name[1:] if len(name) > 1 else name.upper()


def sync_fipe_vehicles(*, max_brands: int = 50, sleep_seconds: float = 0.15) -> dict:
    """
    Importa marcas/modelos da FIPE.
    Cria faixa de anos ampla (1990–ano atual+1) por modelo base.
    """
    brands_payload = _fetch_json(f'{FIPE_BASE}/marcas')
    if not isinstance(brands_payload, list):
        return {'brands': 0, 'models': 0, 'error': 'Não foi possível consultar a FIPE.'}

    created_brands = 0
    created_models = 0
    updated_models = 0
    current_year = date.today().year + 1

    for entry in brands_payload[:max_brands]:
        fipe_code = entry.get('codigo')
        fipe_name = entry.get('nome') or ''
        if not fipe_code:
            continue

        brand_name = _canonical_brand(fipe_name)
        if not brand_name:
            continue

        brand_slug = slugify(brand_name)
        brand, b_created = VehicleBrand.objects.get_or_create(
            slug=brand_slug,
            defaults={'name': brand_name, 'is_active': True},
        )
        if b_created:
            created_brands += 1
        elif brand.name != brand_name:
            brand.name = brand_name
            brand.is_active = True
            brand.save(update_fields=['name', 'is_active'])

        models_payload = _fetch_json(f'{FIPE_BASE}/marcas/{fipe_code}/modelos')
        if not isinstance(models_payload, dict):
            time.sleep(sleep_seconds)
            continue

        seen_bases: set[str] = set()
        for model_entry in models_payload.get('modelos') or []:
            raw_name = model_entry.get('nome') or ''
            base = _base_model_name(raw_name)
            if len(base) < 2 or base.lower() in seen_bases:
                continue
            seen_bases.add(base.lower())

            mslug = slugify(base)
            if not mslug:
                continue

            _, m_created = VehicleModel.objects.update_or_create(
                brand=brand,
                slug=mslug,
                defaults={
                    'name': base,
                    'year_start': 1990,
                    'year_end': current_year,
                    'is_active': True,
                },
            )
            if m_created:
                created_models += 1
            else:
                updated_models += 1

        time.sleep(sleep_seconds)

    return {
        'brands_created': created_brands,
        'models_created': created_models,
        'models_updated': updated_models,
        'brands_total': VehicleBrand.objects.filter(is_active=True).count(),
        'models_total': VehicleModel.objects.filter(is_active=True).count(),
    }
