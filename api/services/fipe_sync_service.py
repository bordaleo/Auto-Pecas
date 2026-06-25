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

# Marcas mais buscadas no Brasil — sincronizadas antes das demais na FIPE.
PRIORITY_BRAND_NAMES = frozenset({
    'Volkswagen', 'Fiat', 'Chevrolet', 'Ford', 'Hyundai', 'Toyota', 'Honda',
    'Renault', 'Jeep', 'Nissan', 'BMW', 'Mercedes-Benz', 'Audi', 'Peugeot',
    'Citroen', 'Mitsubishi', 'Kia', 'Volvo', 'RAM', 'Land Rover', 'Chery', 'JAC',
    'Mini', 'Porsche', 'Subaru', 'Suzuki', 'BYD', 'GWM', 'CAOA Chery',
})


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


def _ordered_fipe_brands(brands_payload: list) -> list[dict]:
    """Prioriza marcas populares; depois ordena alfabeticamente."""
    priority = []
    rest = []
    for entry in brands_payload:
        canonical = _canonical_brand(entry.get('nome') or '')
        if canonical in PRIORITY_BRAND_NAMES:
            priority.append(entry)
        else:
            rest.append(entry)
    priority.sort(key=lambda e: _canonical_brand(e.get('nome') or ''))
    rest.sort(key=lambda e: (e.get('nome') or '').lower())
    return priority + rest


def _sync_brand_models(brand: VehicleBrand, fipe_code: str, *, sleep_seconds: float = 0.15) -> tuple[int, int]:
    """Importa modelos FIPE de uma marca. Retorna (criados, atualizados)."""
    models_payload = _fetch_json(f'{FIPE_BASE}/marcas/{fipe_code}/modelos')
    if not isinstance(models_payload, dict):
        time.sleep(sleep_seconds)
        return 0, 0

    created_models = 0
    updated_models = 0
    current_year = date.today().year + 1
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
    return created_models, updated_models


def _find_fipe_entry(brands_payload: list, *, brand_slug: str = '', brand_name: str = '') -> dict | None:
    slug = (brand_slug or '').strip().lower()
    name = (brand_name or '').strip().lower()
    for entry in brands_payload:
        canonical = _canonical_brand(entry.get('nome') or '')
        if slug and slugify(canonical) == slug:
            return entry
        if name and canonical.lower() == name:
            return entry
        if name and name in (entry.get('nome') or '').lower():
            return entry
    return None


def sync_fipe_brand(*, brand_slug: str = '', brand_name: str = '', sleep_seconds: float = 0.15) -> dict:
    """Sincroniza modelos FIPE de uma única marca (por slug ou nome)."""
    brands_payload = _fetch_json(f'{FIPE_BASE}/marcas')
    if not isinstance(brands_payload, list):
        return {'error': 'Não foi possível consultar a FIPE.'}

    entry = _find_fipe_entry(brands_payload, brand_slug=brand_slug, brand_name=brand_name)
    if not entry:
        return {'error': f'Marca não encontrada na FIPE: {brand_slug or brand_name}.'}

    fipe_code = entry.get('codigo')
    brand_name_canonical = _canonical_brand(entry.get('nome') or '')
    if not fipe_code or not brand_name_canonical:
        return {'error': 'Entrada FIPE inválida.'}

    brand_slug_final = slugify(brand_name_canonical)
    brand, _ = VehicleBrand.objects.get_or_create(
        slug=brand_slug_final,
        defaults={'name': brand_name_canonical, 'is_active': True},
    )
    if brand.name != brand_name_canonical:
        brand.name = brand_name_canonical
        brand.is_active = True
        brand.save(update_fields=['name', 'is_active'])

    created, updated = _sync_brand_models(brand, fipe_code, sleep_seconds=sleep_seconds)
    model_count = VehicleModel.objects.filter(brand=brand, is_active=True).count()
    return {
        'brand': brand_name_canonical,
        'brand_slug': brand_slug_final,
        'models_created': created,
        'models_updated': updated,
        'models_total': model_count,
    }


def sync_fipe_vehicles(*, max_brands: int = 0, sleep_seconds: float = 0.15) -> dict:
    """
    Importa marcas/modelos da FIPE.
    max_brands=0 importa todas as marcas disponíveis.
    Marcas populares no Brasil são sincronizadas primeiro.
    """
    brands_payload = _fetch_json(f'{FIPE_BASE}/marcas')
    if not isinstance(brands_payload, list):
        return {'brands': 0, 'models': 0, 'error': 'Não foi possível consultar a FIPE.'}

    ordered = _ordered_fipe_brands(brands_payload)
    if max_brands > 0:
        ordered = ordered[:max_brands]

    created_brands = 0
    created_models = 0
    updated_models = 0

    for entry in ordered:
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

        c, u = _sync_brand_models(brand, fipe_code, sleep_seconds=sleep_seconds)
        created_models += c
        updated_models += u

    return {
        'brands_created': created_brands,
        'models_created': created_models,
        'models_updated': updated_models,
        'brands_total': VehicleBrand.objects.filter(is_active=True).count(),
        'models_total': VehicleModel.objects.filter(is_active=True).count(),
    }


def schedule_full_fipe_sync() -> bool:
    """Dispara sync completo da FIPE em background (nunca bloqueia HTTP)."""
    import threading
    from django.core.cache import cache

    lock_key = 'galelugi_fipe_sync_full'
    if not cache.add(lock_key, 1, 7200):
        return False

    def _run():
        try:
            sync_fipe_vehicles(max_brands=0)
        except Exception as exc:
            logger.warning('FIPE full background sync failed: %s', exc)
        finally:
            cache.delete(lock_key)

    threading.Thread(target=_run, daemon=True).start()
    return True


def ensure_brand_models_synced(brand_slug: str, *, min_models: int = 12) -> bool:
    """
    Dispara sync FIPE em background se o catálogo local estiver incompleto.
    Nunca bloqueia a requisição HTTP.
    """
    import threading
    from django.core.cache import cache

    brand = VehicleBrand.objects.filter(slug=brand_slug, is_active=True).first()
    if not brand:
        return False
    count = VehicleModel.objects.filter(brand=brand, is_active=True).count()
    if count >= min_models:
        return False

    lock_key = f'galelugi_fipe_sync_{brand_slug}'
    if not cache.add(lock_key, 1, 7200):
        return False

    def _run():
        try:
            sync_fipe_brand(brand_slug=brand_slug)
        except Exception as exc:
            logger.warning('FIPE background sync failed for %s: %s', brand_slug, exc)
        finally:
            cache.delete(lock_key)

    threading.Thread(target=_run, daemon=True).start()
    return True
