import logging
import re

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Order, OrderGroup
from api.serializers.payment import PaymentStatusSerializer
from api.services.order_payment_service import apply_mp_payment, payable_amount
from api.services.payment_service import payment_service

logger = logging.getLogger(__name__)


def _find_order(payment_info: dict, payment_id: str) -> Order | None:
    external_reference = payment_info.get("external_reference")
    if external_reference:
        group_match = re.match(r"^group_(\d+)_user_(\d+)$", str(external_reference))
        if group_match:
            try:
                group = OrderGroup.objects.get(id=int(group_match.group(1)))
                return group.orders.first()
            except OrderGroup.DoesNotExist:
                pass
        match = re.match(r"^order_(\d+)_user_(\d+)$", str(external_reference))
        if match:
            try:
                return Order.objects.get(id=int(match.group(1)))
            except Order.DoesNotExist:
                pass
    order = Order.objects.filter(payment_id=str(payment_id)).first()
    if order:
        return order
    pref = payment_info.get("preference_id")
    if pref:
        group = OrderGroup.objects.filter(payment_preference_id=pref).first()
        if group:
            return group.orders.first()
        return Order.objects.filter(payment_preference_id=pref).first()
    return None


def _order_for_preference(preference_id: str, user) -> Order | None:
    """Pedido principal da preferência. Em checkout multi-vendedor, todos os sub-pedidos a compartilham."""
    return (
        Order.objects.filter(payment_preference_id=preference_id, user=user)
        .select_related("order_group")
        .order_by("pk")
        .first()
    )


class PaymentProcessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        preference_id = request.data.get("preference_id")
        form_data = request.data.get("form_data") or {}
        if not preference_id:
            return Response({"detail": "preference_id é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(form_data, dict):
            return Response({"detail": "form_data inválido."}, status=status.HTTP_400_BAD_REQUEST)

        order = _order_for_preference(preference_id, request.user)
        if not order:
            return Response({"detail": "Pedido não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        payload = dict(form_data)
        payload["transaction_amount"] = float(payable_amount(order))
        payload["description"] = f"Pedido Galelugi Peças #{order.id}"
        payload["external_reference"] = (
            f"group_{order.order_group_id}_user_{request.user.id}"
            if order.order_group_id
            else f"order_{order.id}_user_{request.user.id}"
        )
        payer = payload.get("payer") or {}
        if not isinstance(payer, dict):
            payer = {}
        if not payer.get("email"):
            payer["email"] = (order.order_email or request.user.email or "").strip()
        payload["payer"] = payer

        payment = payment_service.create_payment(payload)
        if not payment:
            if payment_service.last_payment_create_was_incomplete_or_abandoned():
                return Response({
                    "detail": "Pagamento não concluído. Tente novamente na mesma tela.",
                    "error_code": "payment_not_completed",
                }, status=status.HTTP_400_BAD_REQUEST)
            return Response({"detail": "Não foi possível processar o pagamento."}, status=status.HTTP_400_BAD_REQUEST)

        if not payment.get("payment_method_id") and order.payment_method:
            payment = {**payment, "payment_method_id": order.payment_method}
        mp_status = apply_mp_payment(order, payment)

        tx = (payment.get("point_of_interaction") or {}).get("transaction_data") or {}
        return Response({
            "payment_id": payment.get("id"),
            "status": mp_status,
            "status_detail": payment.get("status_detail"),
            "ticket_url": (payment.get("transaction_details") or {}).get("external_resource_url"),
            "pix_qr_code": tx.get("qr_code"),
            "pix_qr_code_base64": tx.get("qr_code_base64"),
        })


@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            data = request.data
            if data.get("type") != "payment":
                return Response({"status": "ok"})
            payment_id = (data.get("data") or {}).get("id")
            if not payment_id:
                return Response({"status": "error"}, status=status.HTTP_400_BAD_REQUEST)

            payment_info = payment_service.get_payment(str(payment_id))
            if not payment_info:
                return Response({"status": "error"}, status=status.HTTP_400_BAD_REQUEST)

            order = _find_order(payment_info, str(payment_id))
            if not order:
                return Response({"status": "error"}, status=status.HTTP_404_NOT_FOUND)

            apply_mp_payment(order, {**payment_info, "id": payment_info.get("id") or payment_id})
            return Response({"status": "ok"})
        except Exception as e:
            logger.exception("Webhook MP: %s", e)
            return Response({"status": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, preference_id):
        order = _order_for_preference(preference_id, request.user)
        if not order:
            return Response({"detail": "Pedido não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_id:
            payment = payment_service.get_payment(order.payment_id)
            if payment:
                apply_mp_payment(order, payment)
                order.refresh_from_db()

        return Response(PaymentStatusSerializer({
            "order_id": order.id,
            "status": order.status,
            "status_display": order.get_status_display(),
            "payment_id": order.payment_id,
            "payment_method": order.payment_method,
            "payment_preference_id": order.payment_preference_id,
            "amount": payable_amount(order),
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }).data)
