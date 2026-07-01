"""Metadados unificados para filtros do catálogo."""
from django.core.cache import cache
from django.db.models import Count, Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Category, Product, VehicleBrand
from api.services.catalog_search_service import record_search_event
from api.services.popular_search_service import get_popular_searches
from api.serializers.marketplace import VehicleBrandListSerializer
from api.serializers.product import CategorySerializer

CATALOG_FILTERS_CACHE_KEY = 'catalog_filters_v1'
CATALOG_FILTERS_TTL = 300  # 5 minutos


def _build_filters_payload():
    categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    product_brands = list(
        Product.objects.filter(is_active=True)
        .exclude(brand='')
        .values_list('brand', flat=True)
        .distinct()
        .order_by('brand')
    )
    vehicle_brands = (
        VehicleBrand.objects.filter(is_active=True)
        .annotate(model_count=Count('models', filter=Q(models__is_active=True)))
        .order_by('name')
    )
    return {
        'categories': CategorySerializer(categories, many=True).data,
        'product_brands': product_brands,
        'vehicle_brands': VehicleBrandListSerializer(vehicle_brands, many=True).data,
        'popular_searches': get_popular_searches(),
        'filters': {
            'product': [
                'q', 'category', 'brand', 'featured', 'in_stock', 'ordering', 'page', 'page_size',
            ],
            'vehicle': [
                'vehicle_brand', 'vehicle_model', 'vehicle_year',
            ],
        },
        'endpoints': {
            'products': '/api/v1/products/',
            'vehicle_lookup': '/api/v1/vehicles/lookup/',
            'vehicle_models': '/api/v1/vehicles/models/',
            'vehicle_search': '/api/v1/vehicles/search/',
            'search_events': '/api/v1/catalog/search-events/',
        },
    }


class CatalogFiltersView(APIView):
    """Opções de filtro para catálogo e busca por veículo."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        cached = cache.get(CATALOG_FILTERS_CACHE_KEY)
        if cached is not None:
            return Response(cached)

        payload = _build_filters_payload()
        cache.set(CATALOG_FILTERS_CACHE_KEY, payload, CATALOG_FILTERS_TTL)
        return Response(payload)


class CatalogSearchEventView(APIView):
    """Registra buscas, cliques em termos populares e compras atribuídas."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        event_type = (request.data.get('event_type') or '').strip()
        allowed = {'search', 'popular_click', 'purchase'}
        if event_type not in allowed:
            return Response(
                {'detail': 'event_type inválido. Use: search, popular_click, purchase.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        term = (request.data.get('term') or '').strip()[:200]
        if event_type in ('search', 'popular_click') and not term:
            return Response({'detail': 'term é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key or ''

        product_id = request.data.get('product_id')
        try:
            product_id = int(product_id) if product_id else None
        except (TypeError, ValueError):
            product_id = None

        result_count = request.data.get('result_count')
        try:
            result_count = int(result_count) if result_count is not None else None
        except (TypeError, ValueError):
            result_count = None

        record_search_event(
            event_type=event_type,
            term=term,
            session_key=session_key,
            user=request.user,
            filters=request.data.get('filters') or {},
            result_count=result_count,
            product_id=product_id,
            source=(request.data.get('source') or '')[:40],
        )
        from django.core.cache import cache
        from api.views.catalog_views import CATALOG_FILTERS_CACHE_KEY
        cache.delete(CATALOG_FILTERS_CACHE_KEY)
        return Response({'ok': True}, status=status.HTTP_201_CREATED)
