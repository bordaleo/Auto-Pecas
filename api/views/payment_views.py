import json
import logging
import re

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Order, OrderGroup, OrderStatus
from api.serializers.payment import PaymentStatusSerializer
from api.services.payment_service import payment_service

logger = logging.getLogger(__name__)

_MP_OPEN = frozenset({"pending", "in_process", "authorized", "in_mediation"})


def _payment_id_int(payment: dict) -> int:
    try:
        return int(payment.get("id") or 0)
    except (TypeError, ValueError):
        return 0


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
    try:
        return Order.objects.get(payment_id=str(payment_id))
    except Order.DoesNotExist:
        pass
    pref = payment_info.get("preference_id")
    if pref:
        try:
            group = OrderGroup.objects.filter(payment_preference_id=pref).first()
            if group:
                return group.orders.first()
            return Order.objects.get(payment_preference_id=pref)
        except Order.DoesNotExist:
            pass
    return None


def _sync_payment_ids(order, payment_id: str, payment_method: str = ''):
    if order.order_group_id:
        group = order.order_group
        group.payment_id = payment_id
        if payment_method:
            group.payment_method = payment_method
        group.save(update_fields=['payment_id', 'payment_method', 'updated_at'])
        Order.objects.filter(order_group=group).update(
            payment_id=payment_id,
            payment_method=payment_method or group.payment_method,
        )
    else:
        order.payment_id = payment_id
        if payment_method:
            order.payment_method = payment_method
        order.save(update_fields=['payment_id', 'payment_method', 'updated_at'])


class PaymentProcessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        preference_id = request.data.get("preference_id")
        form_data = request.data.get("form_data") or {}
        if not preference_id:
            return Response({"detail": "preference_id é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(form_data, dict):
            return Response({"detail": "form_data inválido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(payment_preference_id=preference_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Pedido não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        payload = dict(form_data)
        payload["transaction_amount"] = float(order.amount)
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

        mp_status = payment.get("status")
        pm = payment.get("payment_method_id") or order.payment_method
        _sync_payment_ids(order, str(payment.get("id") or order.payment_id or ""), pm)
        if mp_status == "approved":
            from api.views.shop_views import approve_shop_order
            approve_shop_order(order)
            order.refresh_from_db()
        elif mp_status in ["rejected", "cancelled", "refunded"]:
            from api.views.shop_views import reject_shop_order
            reject_shop_order(order)
        else:
            order.status = OrderStatus.PENDING
            Order.objects.filter(pk=order.pk).update(status=OrderStatus.PENDING)

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

            mp_status = payment_info.get("status")
            pm = payment_info.get("payment_method_id")
            _sync_payment_ids(order, str(payment_id), pm or '')

            if mp_status == "approved":
                from api.views.shop_views import approve_shop_order
                approve_shop_order(order)
            elif mp_status in ["rejected", "cancelled", "refunded"]:
                from api.views.shop_views import reject_shop_order
                reject_shop_order(order)
            else:
                order.save(update_fields=['updated_at'])

            return Response({"status": "ok"})
        except Exception as e:
            logger.exception("Webhook MP: %s", e)
            return Response({"status": "error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, preference_id):
        try:
            order = Order.objects.get(payment_preference_id=preference_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Pedido não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        if order.payment_id:
            payment = payment_service.get_payment(order.payment_id)
            if payment:
                mp_status = payment.get("status")
                if mp_status == "approved" and order.status != OrderStatus.APPROVED:
                    from api.views.shop_views import approve_shop_order
                    approve_shop_order(order)
                elif mp_status in ["rejected", "cancelled", "refunded"]:
                    from api.views.shop_views import reject_shop_order
                    reject_shop_order(order)
                    order.save(update_fields=['updated_at'])

        return Response(PaymentStatusSerializer({
            "order_id": order.id,
            "status": order.status,
            "status_display": order.get_status_display(),
            "payment_id": order.payment_id,
            "payment_method": order.payment_method,
            "payment_preference_id": order.payment_preference_id,
            "amount": order.amount,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        }).data)
