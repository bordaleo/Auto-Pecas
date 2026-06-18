from rest_framework import serializers
from api.models import SystemConfig


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = [
            'store_name', 'store_tagline', 'store_phone', 'store_whatsapp',
            'store_email', 'store_address', 'free_shipping_min',
            'maintenance_mode', 'maintenance_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class SystemConfigPublicSerializer(serializers.ModelSerializer):
    """Configuração exposta ao front da loja (sem e-mail)."""
    class Meta:
        model = SystemConfig
        fields = ['store_name', 'store_tagline', 'store_address', 'store_phone', 'store_whatsapp', 'free_shipping_min']
