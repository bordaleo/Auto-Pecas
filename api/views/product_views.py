import re
from django.db.models import Q, F
from django.utils.text import slugify
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from api.models import Category, Product, User, OrderItem, OrderStatus, ProductReview
from api.services.stock_reservation_service import get_available_stock, release_expired_reservations
from api.services.product_search_service import (
    apply_text_search,
    apply_vehicle_brand_filter,
    apply_vehicle_model_filter,
    apply_vehicle_year_filter,
    order_products,
)
from api.serializers.product import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductWriteSerializer,
    ProductImageUploadSerializer,
)
from api.services.cloudinary_service import upload_image_if_needed


class IsStaffOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and request.user.is_staff


class CategoryListView(ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by('sort_order', 'name')


class ProductPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductListView(ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer
    pagination_class = ProductPagination

    def get_queryset(self):
        release_expired_reservations()
        from django.db.models import Avg, Count
        qs = (
            Product.objects.filter(is_active=True)
            .select_related('category', 'seller')
            .prefetch_related('vehicle_compatibilities__vehicle_model__brand')
            .annotate(
                avg_rating=Avg('reviews__rating', filter=Q(reviews__is_visible=True)),
                review_count=Count('reviews', filter=Q(reviews__is_visible=True)),
            )
        )
        q = self.request.query_params.get('q', '').strip()
        category = self.request.query_params.get('category', '').strip()
        brand = self.request.query_params.get('brand', '').strip()
        featured = self.request.query_params.get('featured', '').strip()
        in_stock = self.request.query_params.get('in_stock', '').strip()
        vehicle_brand = self.request.query_params.get('vehicle_brand', '').strip()
        vehicle_model = self.request.query_params.get('vehicle_model', '').strip()
        vehicle_year = self.request.query_params.get('vehicle_year', '').strip()
        ordering = self.request.query_params.get('ordering', '').strip()

        if q:
            qs = apply_text_search(qs, q)
        if category:
            qs = qs.filter(category__slug=category)
        if brand:
            qs = qs.filter(brand__iexact=brand)
        if featured in ('1', 'true', 'yes'):
            qs = qs.filter(is_featured=True)
        if vehicle_brand:
            qs = apply_vehicle_brand_filter(qs, vehicle_brand)
        if vehicle_model:
            qs = apply_vehicle_model_filter(qs, vehicle_model)
        if vehicle_year:
            qs = apply_vehicle_year_filter(qs, vehicle_year, strict=bool(vehicle_model))
        if in_stock in ('1', 'true', 'yes'):
            qs = qs.filter(stock__gt=0)
        qs = qs.distinct()
        return order_products(qs, ordering)


class ProductDetailView(RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'
    queryset = Product.objects.filter(is_active=True).select_related(
        'category', 'seller',
    ).prefetch_related(
        'images',
        'vehicle_compatibilities__vehicle_model__brand',
    )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        product = self.get_object()
        from api.models import ProductViewEvent
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key or ''
        ProductViewEvent.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key[:64],
        )
        Product.objects.filter(pk=product.pk).update(view_count=F('view_count') + 1)
        return response


class ProductManageListCreateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        qs = Product.objects.select_related('category').order_by('-created_at')
        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(sku__icontains=q) | Q(oem_code__icontains=q)
            )
        serializer = ProductDetailSerializer(qs[:100], many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        if not data.get('slug'):
            data['slug'] = slugify(data.get('name', ''))
        serializer = ProductWriteSerializer(data=data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save()
        return Response(ProductDetailSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductManageDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_object(self, pk):
        return Product.objects.select_related('category').prefetch_related('images').get(pk=pk)

    def get(self, request, pk):
        try:
            product = self.get_object(pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductDetailSerializer(product).data)

    def put(self, request, pk):
        try:
            product = self.get_object(pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductWriteSerializer(product, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save()
        return Response(ProductDetailSerializer(product).data)

    def delete(self, request, pk):
        try:
            product = self.get_object(pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        product.is_active = False
        product.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageUploadView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = ProductImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            url = upload_image_if_needed(
                serializer.validated_data['image'],
                folder='galelugi/products',
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'url': url})


class ProductBrandsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        brands = (
            Product.objects.filter(is_active=True)
            .exclude(brand='')
            .values_list('brand', flat=True)
            .distinct()
            .order_by('brand')
        )
        return Response(list(brands))
