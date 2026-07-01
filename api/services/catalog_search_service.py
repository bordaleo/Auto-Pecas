"""Registro e agregação de eventos de busca do catálogo."""
from __future__ import annotations

from django.db.models import Count, Q

from api.models import CatalogSearchEvent


def record_search_event(
    *,
    event_type: str,
    term: str = '',
    session_key: str = '',
    user=None,
    filters: dict | None = None,
    result_count: int | None = None,
    product_id: int | None = None,
    source: str = '',
) -> CatalogSearchEvent:
    clean_term = (term or '').strip()[:200]
    return CatalogSearchEvent.objects.create(
        event_type=event_type,
        term=clean_term,
        session_key=(session_key or '')[:64],
        user=user if user and getattr(user, 'is_authenticated', False) else None,
        filters=filters or {},
        result_count=result_count,
        product_id=product_id,
        source=(source or '')[:40],
    )


def get_term_scores(limit: int = 20) -> list[dict]:
    """Pontua termos por cliques, buscas e compras (CTR proxy)."""
    qs = (
        CatalogSearchEvent.objects.filter(term__gt='')
        .values('term')
        .annotate(
            searches=Count('id', filter=Q(event_type=CatalogSearchEvent.EVENT_SEARCH)),
            clicks=Count('id', filter=Q(event_type=CatalogSearchEvent.EVENT_POPULAR_CLICK)),
            purchases=Count('id', filter=Q(event_type=CatalogSearchEvent.EVENT_PURCHASE)),
        )
    )
    scored = []
    for row in qs:
        term = row['term']
        score = row['purchases'] * 10 + row['clicks'] * 3 + row['searches']
        if score > 0:
            scored.append({'q': term, 'count': score})
    scored.sort(key=lambda x: x['count'], reverse=True)
    return scored[:limit]
