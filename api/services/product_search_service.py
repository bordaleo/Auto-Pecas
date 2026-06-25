"""Busca de produtos com tokenização e filtros veiculares unificados."""
from __future__ import annotations

import re

from django.db.models import Q, QuerySet

from api.models import Product

SEARCH_FIELDS = (
    'name', 'sku', 'oem_code', 'brand', 'compatible_vehicles', 'description',
)

TOKEN_SPLIT = re.compile(r'\s+')


def _tokens(q: str) -> list[str]:
    raw = (q or '').strip()
    if not raw:
        return []
    parts = TOKEN_SPLIT.split(raw)
    return [p for p in parts if len(p) >= 2]


def apply_text_search(qs: QuerySet, q: str) -> QuerySet:
    """Cada palavra deve aparecer em ao menos um campo (AND entre tokens)."""
    tokens = _tokens(q)
    if not tokens:
        return qs
    for token in tokens:
        token_q = Q()
        for field in SEARCH_FIELDS:
            token_q |= Q(**{f'{field}__icontains': token})
        qs = qs.filter(token_q)
    return qs


def apply_vehicle_brand_filter(qs: QuerySet, vehicle_brand: str) -> QuerySet:
    if not vehicle_brand:
        return qs
    brand_slug = vehicle_brand.strip()
    brand_name = brand_slug.replace('-', ' ')
    return qs.filter(
        Q(vehicle_compatibilities__vehicle_model__brand__slug=brand_slug)
        | Q(vehicle_compatibilities__vehicle_model__brand__name__iexact=brand_slug)
        | Q(vehicle_compatibilities__vehicle_model__brand__name__icontains=brand_name)
        | Q(compatible_vehicles__icontains=brand_slug)
        | Q(compatible_vehicles__icontains=brand_name)
        | Q(name__icontains=brand_name)
        | Q(description__icontains=brand_name)
    )


def apply_vehicle_model_filter(qs: QuerySet, vehicle_model: str) -> QuerySet:
    if not vehicle_model:
        return qs
    model_slug = vehicle_model.strip()
    model_name = model_slug.replace('-', ' ')
    return qs.filter(
        Q(vehicle_compatibilities__vehicle_model__slug=model_slug)
        | Q(vehicle_compatibilities__vehicle_model__name__iexact=model_slug)
        | Q(vehicle_compatibilities__vehicle_model__name__icontains=model_name)
        | Q(compatible_vehicles__icontains=model_name)
        | Q(name__icontains=model_name)
        | Q(description__icontains=model_name)
    )


def apply_vehicle_year_filter(qs: QuerySet, vehicle_year: str, *, strict: bool = False) -> QuerySet:
    if not vehicle_year:
        return qs
    try:
        y = int(vehicle_year)
    except ValueError:
        return qs
    specific_year = (
        Q(vehicle_compatibilities__year_start__isnull=False)
        & Q(vehicle_compatibilities__year_start__lte=y)
        & Q(vehicle_compatibilities__year_end__gte=y)
    )
    all_years = (
        Q(vehicle_compatibilities__year_start__isnull=True)
        & Q(vehicle_compatibilities__year_end__isnull=True)
        & Q(vehicle_compatibilities__vehicle_model__year_start__lte=y)
        & Q(vehicle_compatibilities__vehicle_model__year_end__gte=y)
    )
    year_q = specific_year | all_years
    if strict:
        return qs.filter(year_q).distinct()
    year_text = Q(compatible_vehicles__icontains=str(y)) | Q(name__icontains=str(y))
    return qs.filter(year_q | year_text).distinct()


def order_products(qs: QuerySet, ordering: str = '') -> QuerySet:
    ordering = (ordering or '').strip().lower()
    if ordering in ('price', 'price_asc'):
        return qs.order_by('price', '-is_featured')
    if ordering in ('-price', 'price_desc'):
        return qs.order_by('-price', '-is_featured')
    if ordering in ('name', 'name_asc'):
        return qs.order_by('name')
    return qs.order_by('-is_featured', '-created_at')
