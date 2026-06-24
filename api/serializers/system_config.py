from rest_framework import serializers
from api.models import SystemConfig


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = [
            'store_name', 'store_tagline', 'store_phone', 'store_whatsapp',
            'store_email', 'store_address', 'free_shipping_min',
            'marketplace_commission_percent', 'origin_zip', 'melhor_envio_token',
            'melhor_envio_sandbox', 'stock_reservation_minutes', 'minimum_payout_amount',
            'maintenance_mode', 'maintenance_message',
            'google_analytics_id', 'meta_pixel_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class SystemConfigPublicSerializer(serializers.ModelSerializer):
    """Configuração exposta ao front da loja (sem e-mail)."""
    official_seller = serializers.SerializerMethodField()

    class Meta:
        model = SystemConfig
        fields = [
            'store_name', 'store_tagline', 'store_address', 'store_phone', 'store_whatsapp',
            'free_shipping_min', 'marketplace_commission_percent',
            'google_analytics_id', 'meta_pixel_id', 'official_seller',
        ]

    def get_official_seller(self, obj):
        from api.models import Seller
        seller = Seller.objects.filter(is_official=True, status=Seller.Status.ACTIVE).first()
        if not seller:
            return None
        return {
            'id': seller.id,
            'store_name': seller.store_name,
            'slug': seller.slug,
            'description': seller.description,
        }
