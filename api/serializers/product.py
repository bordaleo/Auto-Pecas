from decimal import Decimal
from rest_framework import serializers
from django.utils.text import slugify
from api.models import Category, Product, ProductImage, ProductVehicleCompatibility
from api.services.seo_service import build_product_seo
from api.services.stock_reservation_service import get_available_stock, release_expired_reservations


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
    in_stock = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    seller_slug = serializers.SerializerMethodField()
    seller_is_official = serializers.SerializerMethodField()
    seller_ships_from_platform = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    vehicle_models = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'sku', 'oem_code', 'brand', 'price', 'compare_at_price',
            'stock', 'in_stock', 'available_stock', 'image_url', 'is_featured', 'category_name', 'category_slug',
            'compatible_vehicles', 'vehicle_models', 'seller_name', 'seller_slug', 'seller_is_official', 'seller_ships_from_platform',
            'average_rating', 'review_count',
            'part_condition', 'part_origin', 'warranty_days',
        ]

    def _seller_meta(self, obj):
        cache = getattr(self, '_seller_meta_cache', None)
        if cache is None:
            self._seller_meta_cache = {}
            cache = self._seller_meta_cache
        if obj.id in cache:
            return cache[obj.id]
        from api.models import SystemConfig
        if obj.seller_id:
            cache[obj.id] = {
                'name': obj.seller.store_name,
                'slug': obj.seller.slug,
                'is_official': obj.seller.is_official,
                'ships_from_platform': obj.seller.ships_from_platform,
            }
        else:
            config = SystemConfig.get_config()
            cache[obj.id] = {
                'name': config.store_name or 'Galelugi Peças',
                'slug': '',
                'is_official': True,
                'ships_from_platform': True,
            }
        return cache[obj.id]

    def get_seller_name(self, obj):
        return self._seller_meta(obj)['name']

    def get_seller_slug(self, obj):
        return self._seller_meta(obj)['slug']

    def get_seller_is_official(self, obj):
        return self._seller_meta(obj)['is_official']

    def get_seller_ships_from_platform(self, obj):
        return self._seller_meta(obj)['ships_from_platform']

    def get_in_stock(self, obj):
        return self.get_available_stock(obj) > 0

    def get_available_stock(self, obj):
        release_expired_reservations()
        return get_available_stock(obj)

    def get_average_rating(self, obj):
        if hasattr(obj, 'avg_rating'):
            return round(float(obj.avg_rating or 0), 1)
        return 0

    def get_review_count(self, obj):
        if hasattr(obj, 'review_count'):
            return obj.review_count or 0
        return 0

    def get_vehicle_models(self, obj):
        links = getattr(obj, '_prefetched_objects_cache', {}).get('vehicle_compatibilities')
        if links is None:
            links = obj.vehicle_compatibilities.select_related('vehicle_model__brand').all()
        return [
            {
                'name': link.vehicle_model.name,
                'slug': link.vehicle_model.slug,
                'brand_slug': link.vehicle_model.brand.slug,
                'year_start': link.year_start if link.year_start is not None else link.vehicle_model.year_start,
                'year_end': link.year_end if link.year_end is not None else link.vehicle_model.year_end,
            }
            for link in links
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    in_stock = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()
    seller_name = serializers.SerializerMethodField()
    seller_slug = serializers.SerializerMethodField()
    seller_id = serializers.IntegerField(source='seller.id', read_only=True, allow_null=True)
    seller_is_official = serializers.SerializerMethodField()
    seller_ships_from_platform = serializers.SerializerMethodField()
    sales_count = serializers.SerializerMethodField()
    sales_revenue = serializers.SerializerMethodField()
    seo_title = serializers.SerializerMethodField()
    seo_description = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    vehicle_models = serializers.SerializerMethodField()
    margin = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'sku', 'oem_code', 'brand', 'price', 'cost_price',
            'compare_at_price', 'stock', 'in_stock', 'available_stock', 'image_url', 'is_featured', 'is_active',
            'compatible_vehicles', 'vehicle_models', 'category', 'images', 'seller_name', 'seller_slug', 'seller_id',
            'seller_is_official', 'seller_ships_from_platform',
            'sales_count', 'sales_revenue', 'average_rating', 'review_count', 'margin',
            'weight_kg', 'width_cm', 'height_cm', 'length_cm',
            'part_condition', 'part_origin', 'warranty_days',
            'seo_title', 'seo_description', 'created_at', 'updated_at',
        ]

    def _seller_meta(self, obj):
        from api.models import SystemConfig
        if obj.seller_id:
            return {
                'name': obj.seller.store_name,
                'slug': obj.seller.slug,
                'is_official': obj.seller.is_official,
                'ships_from_platform': obj.seller.ships_from_platform,
            }
        config = SystemConfig.get_config()
        return {
            'name': config.store_name or 'Galelugi Peças',
            'slug': '',
            'is_official': True,
            'ships_from_platform': True,
        }

    def get_seller_name(self, obj):
        return self._seller_meta(obj)['name']

    def get_seller_slug(self, obj):
        return self._seller_meta(obj)['slug']

    def get_seller_is_official(self, obj):
        return self._seller_meta(obj)['is_official']

    def get_seller_ships_from_platform(self, obj):
        return self._seller_meta(obj)['ships_from_platform']

    def get_in_stock(self, obj):
        return self.get_available_stock(obj) > 0

    def get_available_stock(self, obj):
        release_expired_reservations()
        return get_available_stock(obj)

    def get_average_rating(self, obj):
        if hasattr(obj, 'avg_rating'):
            return round(float(obj.avg_rating or 0), 1)
        from django.db.models import Avg
        from api.models import ProductReview
        avg = ProductReview.objects.filter(product=obj, is_visible=True).aggregate(a=Avg('rating'))['a']
        return round(float(avg or 0), 1)

    def get_review_count(self, obj):
        if hasattr(obj, 'review_count'):
            return obj.review_count or 0
        from api.models import ProductReview
        return ProductReview.objects.filter(product=obj, is_visible=True).count()

    def get_vehicle_models(self, obj):
        links = obj.vehicle_compatibilities.select_related('vehicle_model__brand').all()
        return [
            {
                'id': l.vehicle_model_id,
                'name': l.vehicle_model.name,
                'brand': l.vehicle_model.brand.name,
                'brand_slug': l.vehicle_model.brand.slug,
                'year_start': l.year_start if l.year_start is not None else l.vehicle_model.year_start,
                'year_end': l.year_end if l.year_end is not None else l.vehicle_model.year_end,
                'compat_year_start': l.year_start,
                'compat_year_end': l.year_end,
            }
            for l in links
        ]

    def get_margin(self, obj):
        if obj.cost_price is None:
            return None
        margin = obj.price - obj.cost_price
        pct = (margin / obj.price * 100) if obj.price else 0
        return {'amount': str(margin.quantize(Decimal('0.01'))), 'percent': round(float(pct), 1)}

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


class VehicleCompatEntrySerializer(serializers.Serializer):
    model_id = serializers.IntegerField()
    year_start = serializers.IntegerField(required=False, allow_null=True)
    year_end = serializers.IntegerField(required=False, allow_null=True)


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
            'name', 'slug', 'description', 'sku', 'oem_code', 'brand', 'price', 'cost_price',
            'compare_at_price', 'stock', 'image_url', 'is_active', 'is_featured',
            'compatible_vehicles', 'category', 'extra_images',
            'weight_kg', 'width_cm', 'height_cm', 'length_cm',
            'vehicle_model_ids', 'vehicle_compatibility',
            'part_condition', 'part_origin', 'warranty_days',
        ]
        extra_kwargs = {
            'cost_price': {'required': False, 'allow_null': True},
            'weight_kg': {'required': False},
            'width_cm': {'required': False},
            'height_cm': {'required': False},
            'length_cm': {'required': False},
        }

    vehicle_model_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True,
    )
    vehicle_compatibility = VehicleCompatEntrySerializer(many=True, required=False, write_only=True)

    def validate_slug(self, value):
        slug = slugify(value) if value else ''
        if not slug:
            raise serializers.ValidationError('Slug inválido.')
        return slug

    def validate_image_url(self, value):
        if self.context.get('require_image') and not (value or '').strip():
            raise serializers.ValidationError('Envie uma foto real da peça antes de publicar.')
        return value

    def _format_compat_label(self, model, year_start, year_end):
        if year_start is not None and year_end is not None:
            if year_start == year_end:
                years = str(year_start)
            else:
                years = f'{year_start}-{year_end}'
        else:
            years = f'{model.year_start}-{model.year_end}'
        return f'{model.brand.name} {model.name} ({years})'

    def _sync_vehicle_compat(self, product, compat_entries, model_ids):
        from api.models import VehicleModel

        if compat_entries is None and model_ids is None:
            return

        ProductVehicleCompatibility.objects.filter(product=product).delete()
        labels = []
        seen = set()

        if compat_entries is not None:
            for entry in compat_entries:
                mid = entry['model_id']
                ys = entry.get('year_start')
                ye = entry.get('year_end')
                if ys is not None and ye is None:
                    ye = ys
                if ye is not None and ys is None:
                    ys = ye
                key = (mid, ys, ye)
                if key in seen:
                    continue
                seen.add(key)
                ProductVehicleCompatibility.objects.create(
                    product=product,
                    vehicle_model_id=mid,
                    year_start=ys,
                    year_end=ye,
                )
                try:
                    model = VehicleModel.objects.select_related('brand').get(pk=mid)
                    labels.append(self._format_compat_label(model, ys, ye))
                except VehicleModel.DoesNotExist:
                    continue
        elif model_ids is not None:
            for mid in model_ids:
                key = (mid, None, None)
                if key in seen:
                    continue
                seen.add(key)
                ProductVehicleCompatibility.objects.create(
                    product=product,
                    vehicle_model_id=mid,
                    year_start=None,
                    year_end=None,
                )
                try:
                    model = VehicleModel.objects.select_related('brand').get(pk=mid)
                    labels.append(self._format_compat_label(model, None, None))
                except VehicleModel.DoesNotExist:
                    continue

        product.compatible_vehicles = ', '.join(labels)
        product.save(update_fields=['compatible_vehicles', 'updated_at'])

    def create(self, validated_data):
        extra_images = validated_data.pop('extra_images', [])
        model_ids = validated_data.pop('vehicle_model_ids', None)
        compat_entries = validated_data.pop('vehicle_compatibility', None)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])
        product = Product.objects.create(**validated_data)
        for i, url in enumerate(extra_images):
            ProductImage.objects.create(product=product, url=url, sort_order=i)
        self._sync_vehicle_compat(product, compat_entries, model_ids)
        return product

    def update(self, instance, validated_data):
        extra_images = validated_data.pop('extra_images', None)
        model_ids = validated_data.pop('vehicle_model_ids', None)
        compat_entries = validated_data.pop('vehicle_compatibility', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if extra_images is not None:
            instance.images.all().delete()
            for i, url in enumerate(extra_images):
                ProductImage.objects.create(product=instance, url=url, sort_order=i)
        self._sync_vehicle_compat(instance, compat_entries, model_ids)
        return instance


class ProductImageUploadSerializer(serializers.Serializer):
    image = serializers.CharField(help_text="URL ou base64 da imagem")
