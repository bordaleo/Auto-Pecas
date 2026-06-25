"""Decodificação VIN / placa → veículos compatíveis."""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from datetime import date
from typing import Any

from django.conf import settings
from django.db.models import F, Q

from api.models import Product, ProductVehicleCompatibility, VehicleBrand, VehicleModel

logger = logging.getLogger(__name__)

VIN_WMI_BRANDS = {
    '9BW': 'Volkswagen', 'WVW': 'Volkswagen', 'VWV': 'Volkswagen',
    '9BF': 'Ford', '1FA': 'Ford', '3FA': 'Ford',
    '9BG': 'Chevrolet', '1G1': 'Chevrolet',
    '9BD': 'Fiat', 'ZFA': 'Fiat',
    '93H': 'Honda', '1HG': 'Honda', 'JHM': 'Honda',
    '9BR': 'Toyota', 'JTD': 'Toyota', '2T1': 'Toyota',
    '93Y': 'Renault', 'VF1': 'Renault',
    'KMH': 'Hyundai', '5NP': 'Hyundai',
    '93R': 'Nissan', 'JN1': 'Nissan',
}

BRAND_ALIASES = {
    'vw': 'Volkswagen',
    'volkswagen': 'Volkswagen',
    'volks': 'Volkswagen',
    'gm': 'Chevrolet',
    'chevrolet': 'Chevrolet',
    'chevy': 'Chevrolet',
    'fiat': 'Fiat',
    'ford': 'Ford',
    'honda': 'Honda',
    'toyota': 'Toyota',
    'renault': 'Renault',
    'hyundai': 'Hyundai',
    'nissan': 'Nissan',
    'jeep': 'Jeep',
    'bmw': 'BMW',
    'mercedes': 'Mercedes-Benz',
    'mercedes-benz': 'Mercedes-Benz',
    'audi': 'Audi',
    'peugeot': 'Peugeot',
    'citroen': 'Citroen',
    'citroën': 'Citroen',
    'kia': 'Kia',
    'mitsubishi': 'Mitsubishi',
    'chery': 'Chery',
    'ram': 'RAM',
}


def _normalize_match_text(text: str) -> str:
    text = (text or '').lower()
    text = re.sub(r'[^a-z0-9\s-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _model_match_score(db_name: str, hint: str) -> int:
    db = _normalize_match_text(db_name)
    h = _normalize_match_text(hint)
    if not h or not db:
        return 0
    if db == h:
        return 100
    if h in db:
        return 92
    if db in h:
        # Evita confundir Gol com Golf, Fit com Fit... (nomes curtos dentro de outros)
        if len(db) < 4 and len(h) != len(db):
            return 0
        return 88
    db_parts = db.split()
    h_parts = h.split()
    if db_parts[0] == h_parts[0]:
        return 78
    if db_parts[0].startswith(h_parts[0]) or h_parts[0].startswith(db_parts[0]):
        return 68
    if any(part in db for part in h_parts if len(part) >= 3):
        return 55
    return 0


def _clean_model_hint(raw: str) -> str:
    name = (raw or '').strip()
    if '/' in name:
        name = name.split('/')[-1]
    name = re.sub(r'^(VW|GM|FORD|MERCEDES|BMW|AUDI)\s*[-/]?\s*', '', name, flags=re.I)
    name = re.sub(r'\s+\d[\d,.]*.*$', '', name)
    name = re.sub(
        r'\s+(Flex|Gasolina|Diesel|Híbrido|Hibrido|Elétrico|Eletrico|Manual|Automático|Automatico).*$',
        '',
        name,
        flags=re.I,
    )
    name = name.strip(' -/')
    return name or raw.strip()


def _parse_plate_brand_model(marca: str, modelo: str) -> tuple[str, str]:
    marca = (marca or '').strip()
    modelo = _clean_model_hint(modelo or '')
    if '/' in (marca or ''):
        parts = marca.split('/', 1)
        marca, extra = parts[0], parts[1]
        if not modelo:
            modelo = _clean_model_hint(extra)
    if '/' in modelo:
        modelo = _clean_model_hint(modelo.split('/')[-1])
    return marca, modelo


def normalize_vin(vin: str) -> str:
    return re.sub(r'[^A-HJ-NPR-Z0-9]', '', (vin or '').upper())


def normalize_plate(plate: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', (plate or '').upper())


def _parse_year(value) -> int | None:
    if value in (None, ''):
        return None
    try:
        year = int(str(value).strip()[:4])
    except (TypeError, ValueError):
        return None
    if 1980 <= year <= date.today().year + 1:
        return year
    return None


def _extract_years_from_payload(payload: dict) -> tuple[int | None, bool, int | None, int | None]:
    estimado = bool(payload.get('estimado'))
    fab = _parse_year(
        payload.get('ano_fabricacao') or payload.get('anoFabricacao') or payload.get('fabricacao'),
    )
    mod = _parse_year(
        payload.get('ano_modelo') or payload.get('anoModelo') or payload.get('modelo_ano'),
    )
    generic = _parse_year(payload.get('ano') or payload.get('year'))

    if estimado:
        year = fab or mod or None
    else:
        year = fab or mod or generic

    return year, estimado, fab, mod


def _vin_year_from_code(code: str) -> int | None:
    mapping = {
        'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014, 'F': 2015,
        'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019, 'L': 2020, 'M': 2021,
        'N': 2022, 'P': 2023, 'R': 2024, 'S': 2025, 'T': 2026,
        '1': 2001, '2': 2002, '3': 2003, '4': 2004, '5': 2005,
        '6': 2006, '7': 2007, '8': 2008, '9': 2009,
    }
    return mapping.get(code.upper())


def _model_values(models_or_qs) -> list[dict]:
    if hasattr(models_or_qs, 'values'):
        return list(
            models_or_qs.values(
                'id', 'name', 'slug', 'year_start', 'year_end',
                brand_slug=F('brand__slug'),
            ),
        )
    return [
        {
            'id': vm.id,
            'name': vm.name,
            'slug': vm.slug,
            'year_start': vm.year_start,
            'year_end': vm.year_end,
            'brand_slug': vm.brand.slug,
        }
        for vm in models_or_qs
    ]


def _resolve_brand(name: str) -> VehicleBrand | None:
    if not name:
        return None
    clean = name.strip()
    canonical = BRAND_ALIASES.get(clean.lower(), clean)
    brand = VehicleBrand.objects.filter(name__iexact=canonical, is_active=True).first()
    if brand:
        return brand
    return VehicleBrand.objects.filter(name__icontains=canonical.split()[0], is_active=True).first()


def _match_vehicle_models(brand_name: str, model_name: str, year: int | None) -> list[dict]:
    marca, modelo = _parse_plate_brand_model(brand_name, model_name)
    brand = _resolve_brand(marca)
    clean_model = _clean_model_hint(modelo or model_name or '')

    if not brand and clean_model:
        vm = VehicleModel.objects.filter(
            name__icontains=clean_model.split()[0], is_active=True,
        ).select_related('brand').first()
        if vm:
            brand = vm.brand

    if not brand and marca:
        brand = _resolve_brand(marca.split()[0])

    if not brand:
        return []

    qs = VehicleModel.objects.filter(brand=brand, is_active=True).select_related('brand')
    if year:
        by_year = qs.filter(year_start__lte=year, year_end__gte=year)
        if by_year.exists():
            qs = by_year

    if clean_model and clean_model.lower() not in BRAND_ALIASES:
        scored = []
        for vm in qs:
            score = _model_match_score(vm.name, clean_model)
            if score >= 55:
                scored.append((score, vm))
        if not scored:
            for vm in qs.filter(name__icontains=clean_model.split()[0]):
                scored.append((_model_match_score(vm.name, clean_model), vm))
        scored.sort(key=lambda x: (-x[0], x[1].name))
        if scored:
            return _model_values([vm for _, vm in scored[:8]])

    return _model_values(qs.order_by('name', '-year_end')[:8])


def _apply_year_override(result: dict, year_override) -> dict:
    year = _parse_year(year_override)
    if not year or not result.get('valid'):
        return result

    marca = result.get('brand_hint') or ''
    modelo = result.get('model_hint') or ''
    models = _match_vehicle_models(marca, modelo, year)
    result = {**result, 'year_hint': year, 'year_estimated': False, 'vehicle_models': models}

    parts = []
    if marca or modelo:
        parts.append(f'{marca} {modelo}'.strip())
    if year:
        parts.append(f'Ano {year}')
    result['message'] = ' · '.join(p for p in parts if p) if parts else 'Veículo identificado'
    return result


def _fetch_plate_from_puxarplaca(plate: str) -> dict[str, Any] | None:
    url = getattr(settings, 'PLACA_API_URL', '') or f'https://puxarplaca.com/api/placa.php?placa={plate}'
    if '{plate}' in url:
        url = url.format(plate=plate)
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Galelugi-Pecas/1.0', 'Accept': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode('utf-8', errors='replace'))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        logger.warning('Falha consulta placa %s: %s', plate, exc)
        return None

    if not payload.get('ok'):
        return None

    year, estimado, fab, mod = _extract_years_from_payload(payload)
    return {
        'marca': payload.get('marca') or payload.get('brand') or '',
        'modelo': payload.get('modelo') or payload.get('model') or '',
        'ano': year,
        'ano_fabricacao': fab,
        'ano_modelo': mod,
        'estimado': estimado,
        'cor': payload.get('cor') or '',
        'combustivel': payload.get('combustivel') or '',
        'uf': payload.get('uf') or '',
        'raw': payload,
    }


def decode_vin(vin: str, *, year_override=None) -> dict:
    vin = normalize_vin(vin)
    if len(vin) != 17:
        return {'valid': False, 'detail': 'VIN deve ter 17 caracteres.'}

    wmi = vin[:3]
    year_code = vin[9] if len(vin) > 9 else ''
    brand_hint = VIN_WMI_BRANDS.get(wmi, '')
    year = _parse_year(year_override) or _vin_year_from_code(year_code)
    models = _match_vehicle_models(brand_hint, '', year) if brand_hint else []

    result = {
        'valid': True,
        'vin': vin,
        'brand_hint': brand_hint,
        'year_hint': year,
        'year_estimated': False,
        'vehicle_models': models,
        'message': (
            f'Marca detectada: {brand_hint or "desconhecida"}'
            + (f' · Ano {year}' if year else '')
        ),
    }
    if year_override:
        result = _apply_year_override(result, year_override)
    return result


def lookup_plate(plate: str, *, year_override=None) -> dict:
    plate = normalize_plate(plate)
    if len(plate) not in (7, 8):
        return {'valid': False, 'detail': 'Placa inválida. Use o formato ABC1D23 ou ABC1234.'}

    data = _fetch_plate_from_puxarplaca(plate)
    if not data or not data.get('marca'):
        return {
            'valid': False,
            'detail': 'Não foi possível consultar esta placa agora. Tente o VIN ou filtros manuais.',
        }

    marca = data['marca']
    modelo = data['modelo']
    marca, modelo = _parse_plate_brand_model(marca, modelo)
    year_estimated = bool(data.get('estimado'))
    year = _parse_year(year_override) if year_override else data.get('ano')

    if year_override:
        year_estimated = False

    models = _match_vehicle_models(marca, modelo, year)

    message_parts = [f'{marca} {modelo}'.strip()]
    if year:
        message_parts.append(f'Ano {year}')
    elif year_estimated:
        message_parts.append('Informe o ano do veículo abaixo')

    return {
        'valid': True,
        'plate': plate,
        'brand_hint': marca,
        'model_hint': modelo,
        'year_hint': year,
        'year_estimated': year_estimated and not year_override,
        'vehicle_models': models,
        'plate_data': data,
        'message': ' · '.join(p for p in message_parts if p),
    }


def parse_vehicle_text_query(text: str, *, year_override=None) -> dict:
    raw = (text or '').strip()
    if not raw:
        return {'valid': False, 'detail': 'Informe placa, VIN ou modelo/ano.'}

    normalized = normalize_plate(raw.replace(' ', ''))
    if len(normalized) in (7, 8):
        return lookup_plate(normalized, year_override=year_override)

    if len(normalize_vin(raw)) == 17:
        return decode_vin(raw, year_override=year_override)

    year_match = re.search(r'\b(19|20)\d{2}\b', raw)
    year = _parse_year(year_override) or (int(year_match.group()) if year_match else None)
    tokens = re.sub(r'\b(19|20)\d{2}\b', ' ', raw)
    tokens = re.sub(r'\b\d\.\d\b', ' ', tokens)
    tokens = re.sub(r'\s+', ' ', tokens).strip()
    if not tokens:
        return {'valid': False, 'detail': 'Informe o modelo do veículo (ex.: Polo 2010 1.6).'}

    brand_hint = ''
    model_hint = tokens
    first = tokens.split()[0].lower()
    if first in BRAND_ALIASES:
        brand_hint = BRAND_ALIASES[first]
        model_hint = ' '.join(tokens.split()[1:]) or tokens
    else:
        brand = _resolve_brand(first)
        if brand:
            brand_hint = brand.name
            model_hint = ' '.join(tokens.split()[1:]) or tokens

    models = _match_vehicle_models(brand_hint or first, model_hint, year)

    message_parts = [tokens]
    if year:
        message_parts.append(f'Ano {year}')

    return {
        'valid': True,
        'query': raw,
        'brand_hint': brand_hint,
        'model_hint': model_hint,
        'year_hint': year,
        'year_estimated': False,
        'vehicle_models': models,
        'message': ' · '.join(message_parts),
    }


def find_products_for_vehicle(model_ids: list[int], limit: int = 48, *, brand_hint: str = '', model_hint: str = ''):
    products = []
    if model_ids:
        product_ids = ProductVehicleCompatibility.objects.filter(
            vehicle_model_id__in=model_ids,
        ).values_list('product_id', flat=True).distinct()
        products = list(
            Product.objects.filter(id__in=product_ids, is_active=True)
            .select_related('category', 'seller')[:limit]
        )

    if products:
        return products

    from api.services.product_search_service import apply_text_search

    qs = Product.objects.filter(is_active=True).select_related('category', 'seller')
    search_text = ' '.join(filter(None, [_clean_model_hint(model_hint), brand_hint])).strip()
    if search_text:
        qs = apply_text_search(qs, search_text)
        products = list(qs.distinct()[:limit])
        if products:
            return products

    tokens = []
    clean_model = _clean_model_hint(model_hint)
    if clean_model:
        tokens.append(clean_model.split()[0])
    if brand_hint:
        tokens.append(brand_hint.split()[0])
        alias = BRAND_ALIASES.get(brand_hint.lower())
        if alias:
            tokens.append('VW' if alias == 'Volkswagen' else alias[:4])

    if not tokens:
        return []

    q = Q()
    for token in tokens:
        if len(token) < 2:
            continue
        q |= Q(name__icontains=token)
        q |= Q(compatible_vehicles__icontains=token)
        q |= Q(brand__icontains=token)
        q |= Q(description__icontains=token)

    if not q:
        return []

    return list(
        Product.objects.filter(q, is_active=True)
        .select_related('category', 'seller')
        .distinct()[:limit]
    )
