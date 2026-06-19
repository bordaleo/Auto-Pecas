import re
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from django.utils.text import slugify
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from api.models import Product, Seller, OrderStatus
from api.permissions.seller import IsActiveSeller, get_seller_for_user
from api.serializers.seller import SellerApplySerializer, SellerMeSerializer, SellerPublicSerializer
from api.serializers.product import ProductDetailSerializer, ProductWriteSerializer, ProductImageUploadSerializer
from api.services.cloudinary_service import upload_image_if_needed
from api.services.marketplace_service import seller_dashboard_stats, get_commission_rate, split_sale_amount


def unique_product_slug(name):
    base = slugify(name)[:200] or 'peca'
    slug = base
    counter = 1
    while Product.objects.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


class SellerApplyView(APIView):
    """Cadastro de vendedor no marketplace."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SellerApplySerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        seller = serializer.save()
        return Response(SellerMeSerializer(seller).data, status=status.HTTP_201_CREATED)


class SellerMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        seller = get_seller_for_user(request.user)
        if not seller:
            return Response({'detail': 'Você ainda não é vendedor.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SellerMeSerializer(seller).data)


class SellerCommissionPreviewView(APIView):
    """Simula repasse para o vendedor ao definir preço."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        seller = get_seller_for_user(request.user)
        if not seller or seller.status != Seller.Status.ACTIVE:
            return Response({'detail': 'Loja não ativa.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            price = float(request.data.get('price', 0))
        except (TypeError, ValueError):
            return Response({'detail': 'Preço inválido.'}, status=status.HTTP_400_BAD_REQUEST)
        if price <= 0:
            return Response({'detail': 'Preço inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        fee, earning, rate = split_sale_amount(price, seller)
        return Response({
            'price': f'{price:.2f}',
            'commission_rate': str(rate),
            'platform_fee': str(fee),
            'seller_earning': str(earning),
        })


class SellerProductListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get_seller(self, request):
        if request.user.is_staff:
            return get_seller_for_user(request.user)
        return Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)

    def get(self, request):
        seller = self.get_seller(request)
        if not seller and request.user.is_staff:
            return Response([])
        qs = (
            Product.objects.filter(seller=seller)
            .select_related('category')
            .annotate(
                sales_count=Count(
                    'order_items',
                    filter=Q(order_items__order__status=OrderStatus.APPROVED),
                ),
                sales_revenue=Coalesce(
                    Sum(
                        'order_items__unit_price',
                        filter=Q(order_items__order__status=OrderStatus.APPROVED),
                    ),
                    Decimal('0.00'),
                ),
            )
            .order_by('-created_at')
        )
        return Response(ProductDetailSerializer(qs, many=True).data)

    def post(self, request):
        seller = self.get_seller(request)
        if not seller:
            return Response({'detail': 'Cadastre sua loja primeiro.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        if not data.get('slug'):
            data['slug'] = unique_product_slug(data.get('name', 'peca'))

        serializer = ProductWriteSerializer(
            data=data,
            context={'request': request, 'require_image': True},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product = serializer.save(seller=seller, created_by=request.user)
        return Response(ProductDetailSerializer(product).data, status=status.HTTP_201_CREATED)


class SellerProductDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get_product(self, request, pk):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        return Product.objects.select_related('category').prefetch_related('images').get(pk=pk, seller=seller)

    def put(self, request, pk):
        try:
            product = self.get_product(request, pk)
        except (Product.DoesNotExist, Seller.DoesNotExist):
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductWriteSerializer(
            product, data=request.data, partial=True,
            context={'request': request, 'require_image': False},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save()
        return Response(ProductDetailSerializer(product).data)

    def delete(self, request, pk):
        try:
            product = self.get_product(request, pk)
        except (Product.DoesNotExist, Seller.DoesNotExist):
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        product.is_active = False
        product.save(update_fields=['is_active', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, pk):
        """Ativa/inativa peça rapidamente."""
        try:
            product = self.get_product(request, pk)
        except (Product.DoesNotExist, Seller.DoesNotExist):
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({'detail': 'Informe is_active.'}, status=status.HTTP_400_BAD_REQUEST)
        product.is_active = bool(is_active)
        product.save(update_fields=['is_active', 'updated_at'])
        return Response(ProductDetailSerializer(product).data)


class SellerImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def post(self, request):
        serializer = ProductImageUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            url = upload_image_if_needed(serializer.validated_data['image'], folder='galelugi/products')
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'url': url})


class SellerPublicView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        try:
            seller = Seller.objects.get(slug=slug, status=Seller.Status.ACTIVE)
        except Seller.DoesNotExist:
            return Response({'detail': 'Loja não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        products = Product.objects.filter(seller=seller, is_active=True).select_related('category')[:48]
        return Response({
            'seller': SellerPublicSerializer(seller).data,
            'products': ProductDetailSerializer(products, many=True).data,
        })
