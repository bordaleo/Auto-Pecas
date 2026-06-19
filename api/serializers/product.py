from rest_framework import serializers
from django.utils.text import slugify
from api.models import Category, Product, ProductImage
from api.services.seo_service import build_product_seo


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'description', 'is_active', 'sort_order', 'product_count']

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'url', 'alt_text', 'sort_order']


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    category_slug = serializers.CharField(source='category.slug', read_only=True, default='')
    in_stock = serializers.BooleanField(read_only=True)
    seller_name = serializers.CharField(source='seller.store_name', read_only=True, default='')
    seller_slug = serializers.CharField(source='seller.slug', read_only=True, default='')

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'oem_code', 'brand', 'price', 'compare_at_price',
            'stock', 'in_stock', 'image_url', 'is_featured', 'category_name', 'category_slug',
            'compatible_vehicles', 'seller_name', 'seller_slug',
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    seller_name = serializers.CharField(source='seller.store_name', read_only=True, default='')
    seller_slug = serializers.CharField(source='seller.slug', read_only=True, default='')
    sales_count = serializers.SerializerMethodField()
    sales_revenue = serializers.SerializerMethodField()
    seo_title = serializers.SerializerMethodField()
    seo_description = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'sku', 'oem_code', 'brand', 'price',
            'compare_at_price', 'stock', 'in_stock', 'image_url', 'is_featured', 'is_active',
            'compatible_vehicles', 'category', 'images', 'seller_name', 'seller_slug',
            'sales_count', 'sales_revenue', 'seo_title', 'seo_description',
            'created_at', 'updated_at',
        ]

    def get_seo_title(self, obj):
        return build_product_seo(obj)['seo_title']

    def get_seo_description(self, obj):
        return build_product_seo(obj)['seo_description']

    def get_sales_count(self, obj):
        if hasattr(obj, 'sales_count'):
            return obj.sales_count or 0
        stats = getattr(obj, '_sales_stats', None)
        if stats:
            return stats.get('count', 0)
        return 0

    def get_sales_revenue(self, obj):
        if hasattr(obj, 'sales_revenue'):
            return str(obj.sales_revenue or '0.00')
        stats = getattr(obj, '_sales_stats', None)
        if stats:
            return str(stats.get('revenue', '0.00'))
        return '0.00'


class ProductWriteSerializer(serializers.ModelSerializer):
    extra_images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        write_only=True,
        help_text="URLs de imagens adicionais",
    )

    class Meta:
        model = Product
        fields = [
            'name', 'slug', 'description', 'sku', 'oem_code', 'brand', 'price',
            'compare_at_price', 'stock', 'image_url', 'is_active', 'is_featured',
            'compatible_vehicles', 'category', 'extra_images',
        ]

    def validate_slug(self, value):
        slug = slugify(value) if value else ''
        if not slug:
            raise serializers.ValidationError('Slug inválido.')
        return slug

    def validate_image_url(self, value):
        if self.context.get('require_image') and not (value or '').strip():
            raise serializers.ValidationError('Envie uma foto real da peça antes de publicar.')
        return value

    def create(self, validated_data):
        extra_images = validated_data.pop('extra_images', [])
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])
        product = Product.objects.create(**validated_data)
        for i, url in enumerate(extra_images):
            ProductImage.objects.create(product=product, url=url, sort_order=i)
        return product

    def update(self, instance, validated_data):
        extra_images = validated_data.pop('extra_images', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if extra_images is not None:
            instance.images.all().delete()
            for i, url in enumerate(extra_images):
                ProductImage.objects.create(product=instance, url=url, sort_order=i)
        return instance


class ProductImageUploadSerializer(serializers.Serializer):
    image = serializers.CharField(help_text="URL ou base64 da imagem")
