from rest_framework import serializers
from django.utils.text import slugify
from api.models import Seller


class SellerPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ['id', 'store_name', 'slug', 'description']


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
        ]

    def get_commission_rate_default(self, obj):
        from api.services.marketplace_service import get_commission_rate
        return str(get_commission_rate(obj))

    def get_stats(self, obj):
        from api.services.marketplace_service import seller_dashboard_stats
        return seller_dashboard_stats(obj)


class SellerApplySerializer(serializers.Serializer):
    store_name = serializers.CharField(max_length=120)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    document = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')

    def validate_store_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError('Nome da loja muito curto.')
        return value.strip()

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

        from django.conf import settings
        status = Seller.Status.ACTIVE if settings.DEBUG else Seller.Status.PENDING

        return Seller.objects.create(
            user=user,
            slug=slug,
            status=status,
            phone=validated_data.get('phone') or user.phone or '',
            **{k: v for k, v in validated_data.items() if k != 'phone'},
        )
