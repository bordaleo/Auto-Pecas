"""Busca de produtos com tokenização, sinônimos e filtros veiculares unificados."""
from __future__ import annotations

import re

from django.db.models import Q, QuerySet

from api.models import Product
from api.services.search_synonyms import expand_token, find_phrase_synonyms, tokenize_query

SEARCH_FIELDS = (
    'name', 'sku', 'oem_code', 'brand', 'compatible_vehicles', 'description',
)

TOKEN_SPLIT = re.compile(r'\s+')


def _tokens(q: str) -> list[str]:
    return tokenize_query(q)


def _field_contains(term: str) -> Q:
    q = Q()
    for field in SEARCH_FIELDS:
        q |= Q(**{f'{field}__icontains': term})
    return q


def apply_text_search(qs: QuerySet, q: str) -> QuerySet:
    """Cada palavra deve aparecer em ao menos um campo (AND entre tokens).
    Sinônimos expandem cada token (OR dentro do token). Frases conhecidas usam OR do grupo."""
    raw = (q or '').strip()
    if not raw:
        return qs

    phrase_synonyms = find_phrase_synonyms(raw)
    if phrase_synonyms:
        combined = Q()
        for term in phrase_synonyms:
            combined |= _field_contains(term)
        return qs.filter(combined).distinct()

    tokens = _tokens(raw)
    if not tokens:
        return qs.filter(_field_contains(raw))

    for token in tokens:
        expansions = expand_token(token)
        token_q = Q()
        for exp in expansions:
            token_q |= _field_contains(exp)
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
