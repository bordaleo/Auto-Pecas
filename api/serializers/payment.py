from rest_framework import serializers


class PaymentStatusSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    status = serializers.CharField()
    status_display = serializers.CharField(required=False)
    payment_id = serializers.CharField(required=False, allow_null=True)
    payment_method = serializers.CharField(required=False, allow_null=True)
    payment_preference_id = serializers.CharField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
