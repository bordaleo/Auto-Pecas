"""Termos de busca populares — apenas buscas de texto reais."""
from __future__ import annotations

from django.db.models import Count

from api.models import Category, Product
from api.services.catalog_search_service import get_term_scores

FALLBACK_SEARCHES = [
    'Filtro de óleo VW/Audi',
    'Kit correia dentada Onix/Prisma',
    "Bomba d'água Ford Ka",
    'Alternador 90A Gol/Polo/Fox 1.0/1.6',
    'Fluido de freio DOT',
    'Amortecedor dianteiro Palio/Siena/Strada',
    'Disco de freio ventilado',
    'Pastilha de freio dianteira',
]


def _category_name_keys() -> set[str]:
    return {
        (name or '').strip().lower()
        for name in Category.objects.filter(is_active=True).values_list('name', flat=True)
        if name
    }


def _simplify_product_name(name: str, max_words: int = 4) -> str:
    words = (name or '').split()[:max_words]
    return ' '.join(words).strip()


def get_popular_searches(limit: int = 8) -> list[dict]:
    """Termos mais buscados (analytics), depois peças populares, depois fallback."""
    results: list[dict] = []
    seen: set[str] = set()
    category_keys = _category_name_keys()

    def add(term: str, count: int | None = None) -> None:
        clean = (term or '').strip()
        if not clean or len(clean) < 3:
            return
        key = clean.lower()
        if key in seen or key in category_keys:
            return
        seen.add(key)
        results.append({'q': clean, 'count': count})

    for item in get_term_scores(limit=limit * 2):
        add(item['q'], item['count'])
        if len(results) >= limit:
            return results[:limit]

    popular_products = (
        Product.objects.filter(is_active=True, stock__gt=0)
        .annotate(views=Count('view_events'))
        .order_by('-views', '-view_count', '-is_featured', 'name')[:limit * 2]
    )
    for product in popular_products:
        if len(results) >= limit:
            break
        add(_simplify_product_name(product.name))

    for term in FALLBACK_SEARCHES:
        if len(results) >= limit:
            break
        add(term)

    return results[:limit]
