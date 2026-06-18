import re
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from api.models import Category, Product
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


class ProductListView(ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductListSerializer

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True).select_related('category')
        q = self.request.query_params.get('q', '').strip()
        category = self.request.query_params.get('category', '').strip()
        brand = self.request.query_params.get('brand', '').strip()
        featured = self.request.query_params.get('featured', '').strip()
        in_stock = self.request.query_params.get('in_stock', '').strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(sku__icontains=q)
                | Q(oem_code__icontains=q)
                | Q(brand__icontains=q)
                | Q(compatible_vehicles__icontains=q)
                | Q(description__icontains=q)
            )
        if category:
            qs = qs.filter(category__slug=category)
        if brand:
            qs = qs.filter(brand__iexact=brand)
        if featured in ('1', 'true', 'yes'):
            qs = qs.filter(is_featured=True)
        if in_stock in ('1', 'true', 'yes'):
            qs = qs.filter(stock__gt=0)
        return qs.order_by('-is_featured', '-created_at')


class ProductDetailView(RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductDetailSerializer
    lookup_field = 'slug'
    queryset = Product.objects.filter(is_active=True).select_related('category').prefetch_related('images')


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
                folder='sandroni/products',
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
