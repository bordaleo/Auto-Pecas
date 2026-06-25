"""Metadados unificados para filtros do catálogo."""
from django.db.models import Count, Q
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Category, Product, VehicleBrand
from api.serializers.marketplace import VehicleBrandListSerializer
from api.serializers.product import CategorySerializer


class CatalogFiltersView(APIView):
    """Opções de filtro para catálogo e busca por veículo."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
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

        return Response({
            'categories': CategorySerializer(categories, many=True).data,
            'product_brands': product_brands,
            'vehicle_brands': VehicleBrandListSerializer(vehicle_brands, many=True).data,
            'filters': {
                'product': [
                    'q', 'category', 'brand', 'featured', 'in_stock', 'ordering',
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
            },
        })
