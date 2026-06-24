from rest_framework import serializers
from django.utils.text import slugify
from api.models import Seller
from api.services.shipping_service import normalize_zip


class SellerPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = [
            'id', 'store_name', 'slug', 'description',
            'is_official', 'ships_from_platform',
            'shipping_city', 'shipping_state',
        ]


class SellerMeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    commission_rate_default = serializers.SerializerMethodField()
    stats = serializers.SerializerMethodField()

    class Meta:
        model = Seller
        fields = [
            'id', 'store_name', 'slug', 'description', 'document', 'phone', 'pix_key',
            'status', 'status_display', 'commission_rate', 'commission_rate_default',
            'balance_available', 'balance_pending', 'stats', 'created_at',
            'origin_zip', 'shipping_address', 'shipping_city', 'shipping_state',
            'ships_from_platform', 'is_official', 'estimated_stock_units',
        ]
        read_only_fields = ['is_official', 'status', 'slug', 'estimated_stock_units']

    def get_commission_rate_default(self, obj):
        from api.services.marketplace_service import get_commission_rate
        return str(get_commission_rate(obj))

    def get_stats(self, obj):
        from api.services.marketplace_service import seller_dashboard_stats
        return seller_dashboard_stats(obj)


class SellerProfileUpdateSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    pix_key = serializers.CharField(max_length=120, required=False, allow_blank=True)
    origin_zip = serializers.CharField(max_length=12, required=False, allow_blank=True)
    shipping_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    shipping_city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    shipping_state = serializers.CharField(max_length=2, required=False, allow_blank=True)
    ships_from_platform = serializers.BooleanField(required=False)

    def validate_origin_zip(self, value):
        digits = normalize_zip(value)
        if value and len(digits) != 8:
            raise serializers.ValidationError('CEP deve ter 8 dígitos.')
        return digits

    def validate_shipping_state(self, value):
        return (value or '').strip().upper()[:2]


class SellerApplySerializer(serializers.Serializer):
    store_name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    document = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    origin_zip = serializers.CharField(max_length=12, required=False, allow_blank=True, default='')
    shipping_address = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    shipping_city = serializers.CharField(max_length=120, required=False, allow_blank=True, default='')
    shipping_state = serializers.CharField(max_length=2, required=False, allow_blank=True, default='')
    estimated_stock_units = serializers.IntegerField(min_value=1, max_value=999999)

    def validate_store_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError('Nome da loja muito curto.')
        return value.strip()

    def validate_origin_zip(self, value):
        digits = normalize_zip(value)
        if value and len(digits) != 8:
            raise serializers.ValidationError('CEP deve ter 8 dígitos.')
        return digits

    def create(self, validated_data):
        user = self.context['request'].user
        if Seller.objects.filter(user=user).exists():
            raise serializers.ValidationError('Você já possui cadastro de vendedor.')

        base_slug = slugify(validated_data['store_name'])[:100] or 'loja'
        slug = base_slug
        counter = 1
        while Seller.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        phone = validated_data.pop('phone', '') or user.phone or ''
        shipping_state = (validated_data.pop('shipping_state', '') or '').upper()[:2]

        return Seller.objects.create(
            user=user,
            slug=slug,
            status=Seller.Status.PENDING,
            phone=phone,
            shipping_state=shipping_state,
            **validated_data,
        )
