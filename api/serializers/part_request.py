"""Serializers para pedidos de peça (demanda pública)."""
from decimal import Decimal
from rest_framework import serializers
from api.models import (
    PartRequest, PartRequestConversation, PartRequestMessage,
    PartRequestRating, PartRequestStatus, PartCondition,
)


class PartRequestCreateSerializer(serializers.Serializer):
    description = serializers.CharField(min_length=10, max_length=2000)
    vehicle_brand = serializers.CharField(max_length=80, required=False, allow_blank=True)
    vehicle_model = serializers.CharField(max_length=120, required=False, allow_blank=True)
    vehicle_year = serializers.IntegerField(required=False, allow_null=True, min_value=1980, max_value=2035)
    plate = serializers.CharField(max_length=12, required=False, allow_blank=True)
    vin = serializers.CharField(max_length=17, required=False, allow_blank=True)
    vehicle_query = serializers.CharField(max_length=120, required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    show_phone = serializers.BooleanField(required=False, default=True)


class PartRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requester_name = serializers.CharField(source='requester.name', read_only=True)
    response_count = serializers.IntegerField(read_only=True, default=0)
    days_until_expiry = serializers.SerializerMethodField()

    class Meta:
        model = PartRequest
        fields = [
            'id', 'description', 'vehicle_brand', 'vehicle_model', 'vehicle_year',
            'plate', 'vin', 'requester_zip', 'contact_phone', 'show_phone',
            'status', 'status_display', 'requester_name', 'response_count',
            'expires_at', 'days_until_expiry', 'created_at', 'closed_at',
        ]
        read_only_fields = ['status', 'created_at', 'closed_at', 'expires_at', 'requester_zip']

    def get_days_until_expiry(self, obj):
        if not obj.expires_at or obj.status != PartRequestStatus.OPEN:
            return None
        from django.utils import timezone
        delta = obj.expires_at - timezone.now()
        return max(0, delta.days)


class PartRequestCloseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[PartRequestStatus.CLOSED, PartRequestStatus.FULFILLED])


class PartRequestRespondSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    quote_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=Decimal('0.01'))
    quote_condition = serializers.ChoiceField(
        choices=[c[0] for c in PartCondition.choices], required=False, allow_blank=True,
    )
    quote_delivery_days = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=90)
    quote_product_id = serializers.IntegerField(required=False, allow_null=True)
    quote_notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class PartRequestRatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True)


class PartRequestMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = PartRequestMessage
        fields = ['id', 'sender_name', 'body', 'is_mine', 'created_at']

    def get_is_mine(self, obj):
        req = self.context.get('request')
        if req and req.user.is_authenticated:
            return obj.sender_id == req.user.id
        return False


class PartRequestConversationSerializer(serializers.ModelSerializer):
    request_description = serializers.CharField(source='part_request.description', read_only=True)
    request_id = serializers.IntegerField(source='part_request.id', read_only=True)
    request_status = serializers.CharField(source='part_request.status', read_only=True)
    seller_name = serializers.CharField(source='seller.store_name', read_only=True)
    buyer_name = serializers.CharField(source='buyer.name', read_only=True)
    contact_phone = serializers.SerializerMethodField()
    whatsapp_url = serializers.SerializerMethodField()
    quote_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    quote_condition = serializers.CharField(read_only=True)
    quote_delivery_days = serializers.IntegerField(read_only=True)
    quote_product_name = serializers.CharField(source='quote_product.name', read_only=True, default='')
    quote_product_slug = serializers.CharField(source='quote_product.slug', read_only=True, default='')
    rating = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = PartRequestConversation
        fields = [
            'id', 'request_id', 'request_description', 'request_status',
            'seller_name', 'buyer_name', 'contact_phone', 'whatsapp_url',
            'quote_price', 'quote_condition', 'quote_delivery_days',
            'quote_product_name', 'quote_product_slug', 'rating',
            'last_message_at', 'unread_count', 'last_message',
        ]

    def get_contact_phone(self, obj):
        req = obj.part_request
        if not req.show_phone:
            return ''
        phone = (req.contact_phone or '').strip()
        if phone:
            return phone
        return (req.requester.phone or '').strip()

    def get_whatsapp_url(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ''
        seller = getattr(request.user, 'seller_profile', None)
        if not seller or obj.seller_id != seller.id:
            return ''
        from api.services.part_request_service import build_whatsapp_url_for_request
        return build_whatsapp_url_for_request(obj, obj.seller)

    def get_rating(self, obj):
        try:
            r = obj.rating
        except PartRequestRating.DoesNotExist:
            return None
        return {'rating': r.rating, 'comment': r.comment}

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        if not msg:
            return ''
        return msg.body[:120]
