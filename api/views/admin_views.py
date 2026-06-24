import json
import logging
import secrets
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.authentication.jwt import decode_access_token
from api.models import OpsAlertEvent, SystemConfig, Order, Seller, ShippingStatus

logger = logging.getLogger(__name__)

User = get_user_model()

PAINEL_SESSION_KEY = "painel_gate_ok"


def get_user_from_request(request):
    """Obtém o usuário do request usando JWT (cookie ou header)"""
    user = None
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            try:
                user = User.objects.get(email=payload.get("sub"), is_active=True)
            except User.DoesNotExist:
                pass
    if not user:
        token = request.COOKIES.get("access_token")
        if token:
            payload = decode_access_token(token)
            if payload:
                try:
                    user = User.objects.get(email=payload.get("sub"), is_active=True)
                except User.DoesNotExist:
                    pass
    return user


def is_admin(user):
    return user and (user.is_staff or user.is_superuser)


def painel_api_authorized(request) -> bool:
    """Sessão do painel (senha) OU staff Django OU JWT de staff."""
    if request.session.get(PAINEL_SESSION_KEY):
        return True
    u = getattr(request, "user", None)
    if u and u.is_authenticated and (u.is_staff or u.is_superuser):
        return True
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if payload:
            try:
                ju = User.objects.get(email=payload.get("sub"), is_active=True)
                if ju.is_staff or ju.is_superuser:
                    return True
            except User.DoesNotExist:
                pass
    return False


def painel_gate_required(view):
    @wraps(view)
    def _wrapped(request, *args, **kwargs):
        if request.session.get(PAINEL_SESSION_KEY):
            return view(request, *args, **kwargs)
        nxt = quote(request.get_full_path(), safe="/")
        return redirect(f"/painel/entrar/?next={nxt}")

    return _wrapped


def _safe_painel_next(raw_next: str) -> str:
    if not raw_next or not isinstance(raw_next, str):
        return "/painel/visao/"
    raw_next = raw_next.strip()
    if not raw_next.startswith("/") or raw_next.startswith("//"):
        return "/painel/visao/"
    if not raw_next.startswith("/painel/"):
        return "/painel/visao/"
    if raw_next.startswith("/painel/entrar"):
        return "/painel/visao/"
    return raw_next


@require_http_methods(["GET", "POST"])
@csrf_protect
def painel_entrar(request):
    if request.session.get(PAINEL_SESSION_KEY):
        return redirect(_safe_painel_next(request.GET.get("next") or "/painel/visao/"))
    err = None
    if request.method == "POST":
        password = (request.POST.get("password") or "").strip()
        expected = (getattr(settings, "PAINEL_GATE_PASSWORD", None) or "").strip()
        if not expected:
            err = "Painel desativado: defina PAINEL_GATE_PASSWORD no ambiente."
        elif secrets.compare_digest(password, expected):
            request.session[PAINEL_SESSION_KEY] = True
            request.session.set_expiry(60 * 60 * 12)
            return redirect(_safe_painel_next(request.POST.get("next") or request.GET.get("next")))
        else:
            err = "Senha incorreta."
    return render(
        request,
        "admin/painel_login.html",
        {"error": err, "next": _safe_painel_next(request.GET.get("next") or "/painel/visao/")},
    )


@require_http_methods(["GET", "POST"])
def painel_sair(request):
    request.session.flush()
    return redirect("/painel/entrar/")


def painel_root_redirect(request):
    if request.session.get(PAINEL_SESSION_KEY):
        return redirect("/painel/visao/")
    return redirect("/painel/entrar/")


def _painel_base_context(tab: str):
    return {"painel_tab": tab}


@painel_gate_required
def painel_visao(request):
    return render(request, "admin/painel_visao.html", _painel_base_context("visao"))


@painel_gate_required
def painel_pedidos(request):
    return render(request, "admin/painel_pedidos.html", _painel_base_context("pedidos"))


@painel_gate_required
def painel_pagamentos(request):
    return render(request, "admin/painel_pagamentos.html", _painel_base_context("pagamentos"))


@painel_gate_required
def painel_conteudo(request):
    return render(request, "admin/painel_conteudo.html", _painel_base_context("conteudo"))


@painel_gate_required
def painel_audiencia(request):
    return render(request, "admin/painel_audiencia.html", _painel_base_context("audiencia"))


@painel_gate_required
def painel_config(request):
    config = SystemConfig.get_config()
    ctx = _painel_base_context("config")
    ctx["config"] = config
    return render(request, "admin/painel_config.html", ctx)


@painel_gate_required
def painel_erros(request):
    return render(request, "admin/painel_erros.html", _painel_base_context("erros"))


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def painel_dashboard_api(request):
    if not painel_api_authorized(request):
        return Response({"detail": "Não autorizado."}, status=status.HTTP_403_FORBIDDEN)
    from api.services.admin_dashboard import get_painel_dashboard_slice

    try:
        days = int(request.query_params.get("days", 14))
    except (TypeError, ValueError):
        days = 14
    page = (request.query_params.get("page") or "visao").strip().lower()
    return Response(get_painel_dashboard_slice(page, days))


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def painel_ops_events_api(request):
    if not painel_api_authorized(request):
        return Response({"detail": "Não autorizado."}, status=status.HTTP_403_FORBIDDEN)
    try:
        limit = int(request.query_params.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    try:
        offset = int(request.query_params.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    qs = OpsAlertEvent.objects.order_by("-created_at")[offset : offset + limit]
    total = OpsAlertEvent.objects.count()
    rows = [
        {
            "id": e.id,
            "created_at": e.created_at.isoformat(),
            "category": e.category,
            "message": e.message,
            "detail": e.detail,
            "body_excerpt": e.body_excerpt,
            "extra": e.extra,
        }
        for e in qs
    ]
    return Response({"total": total, "offset": offset, "limit": limit, "results": rows})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def admin_dashboard_stats_api(request):
    """Compatível: mesmas métricas completas (staff JWT ou sessão do painel)."""
    if not painel_api_authorized(request):
        return Response({"detail": "Não autorizado."}, status=status.HTTP_403_FORBIDDEN)
    from api.services.admin_dashboard import get_admin_dashboard_payload

    try:
        days = int(request.query_params.get("days", 14))
    except (TypeError, ValueError):
        days = 14
    return Response(get_admin_dashboard_payload(days=days))


from api.serializers.system_config import SystemConfigSerializer


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def system_config_public_api(request):
    from django.conf import settings
    from api.serializers.system_config import SystemConfigPublicSerializer
    config = SystemConfig.get_config()
    data = SystemConfigPublicSerializer(config).data
    data['mercadopago_public_key'] = getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', '') or ''
    return Response(data)


@api_view(["GET", "PUT"])
@permission_classes([permissions.AllowAny])
def system_config_api(request):
    from api.serializers.system_config import SystemConfigSerializer

    if not painel_api_authorized(request):
        return Response({"detail": "Acesso negado."}, status=status.HTTP_403_FORBIDDEN)
    config = SystemConfig.get_config()
    if request.method == "GET":
        return Response(SystemConfigSerializer(config).data)
    serializer = SystemConfigSerializer(config, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response({"message": "Configurações atualizadas", "config": serializer.data})


def apply_global_changes(config):
    """Placeholder — mantido por compatibilidade com painel legado."""
    pass


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def painel_session_api(request):
    return Response({"authenticated": painel_api_authorized(request)})


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def painel_login_api(request):
    from api.utils_auth import resolve_login_email

    email = resolve_login_email((request.data.get("email") or "").strip())
    password = (request.data.get("password") or "").strip()

    if email and password:
        try:
            user = User.objects.get(email=User.objects.normalize_email(email), is_active=True)
        except User.DoesNotExist:
            return Response({"detail": "Email ou senha incorretos."}, status=status.HTTP_403_FORBIDDEN)
        if not user.check_password(password):
            return Response({"detail": "Email ou senha incorretos."}, status=status.HTTP_403_FORBIDDEN)
        if not (user.is_staff or user.is_superuser):
            return Response({"detail": "Sem permissão de administrador."}, status=status.HTTP_403_FORBIDDEN)
        request.session[PAINEL_SESSION_KEY] = True
        request.session["painel_staff_id"] = user.id
        request.session.set_expiry(60 * 60 * 12)
        return Response({"ok": True, "email": user.email})

    password = (request.data.get("password") or "").strip()
    expected = (getattr(settings, "PAINEL_GATE_PASSWORD", None) or "").strip()
    if not expected:
        return Response(
            {"detail": "Painel desativado: defina PAINEL_GATE_PASSWORD."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if secrets.compare_digest(password, expected):
        request.session[PAINEL_SESSION_KEY] = True
        request.session.set_expiry(60 * 60 * 12)
        return Response({"ok": True})
    return Response({"detail": "Senha incorreta."}, status=status.HTTP_403_FORBIDDEN)


@csrf_exempt
@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def painel_logout_api(request):
    request.session.flush()
    return Response({"ok": True})


@api_view(["GET", "PATCH"])
@permission_classes([permissions.AllowAny])
def painel_order_detail_api(request, order_id):
    if not painel_api_authorized(request):
        return Response({"detail": "Não autorizado."}, status=status.HTTP_403_FORBIDDEN)
    try:
        order = Order.objects.prefetch_related("items").get(pk=order_id)
    except Order.DoesNotExist:
        return Response({"detail": "Pedido não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    from api.serializers.shop import ShopOrderSerializer

    if request.method == "GET":
        return Response(ShopOrderSerializer(order).data)

    data = request.data
    update_fields = ["updated_at"]
    if "tracking_code" in data:
        order.tracking_code = (data.get("tracking_code") or "").strip()
        update_fields.append("tracking_code")
    if "carrier" in data:
        order.carrier = (data.get("carrier") or "").strip()
        update_fields.append("carrier")
    if "shipping_status" in data:
        status_val = data.get("shipping_status")
        valid = {c[0] for c in ShippingStatus.choices}
        if status_val not in valid:
            return Response({"detail": "Status de envio inválido."}, status=status.HTTP_400_BAD_REQUEST)
        order.shipping_status = status_val
        update_fields.append("shipping_status")
        if status_val == ShippingStatus.SHIPPED and not order.shipped_at:
            from django.utils import timezone
            order.shipped_at = timezone.now()
            update_fields.append("shipped_at")
    order.save(update_fields=update_fields)
    return Response(ShopOrderSerializer(order).data)


@api_view(["GET", "PATCH"])
@permission_classes([permissions.AllowAny])
def painel_sellers_api(request):
    if not painel_api_authorized(request):
        return Response({"detail": "Não autorizado."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        status_filter = (request.GET.get("status") or "").strip()
        qs = Seller.objects.select_related("user").order_by("-created_at")
        if status_filter:
            qs = qs.filter(status=status_filter)
        sellers = qs[:100]
        rows = [
            {
                "id": s.id,
                "store_name": s.store_name,
                "slug": s.slug,
                "description": s.description,
                "status": s.status,
                "status_display": s.get_status_display(),
                "document": s.document,
                "phone": s.phone,
                "estimated_stock_units": s.estimated_stock_units,
                "user_email": s.user.email,
                "user_name": s.user.name,
                "user_phone": s.user.phone,
                "origin_zip": s.origin_zip,
                "shipping_address": s.shipping_address,
                "shipping_city": s.shipping_city,
                "shipping_state": s.shipping_state,
                "ships_from_platform": s.ships_from_platform,
                "is_official": s.is_official,
                "admin_notes": s.admin_notes,
                "pix_key": s.pix_key,
                "created_at": s.created_at.isoformat(),
            }
            for s in sellers
        ]
        pending_count = Seller.objects.filter(status=Seller.Status.PENDING).count()
        return Response({"results": rows, "pending_count": pending_count})

    seller_id = request.data.get("id")
    new_status = request.data.get("status")
    is_official = request.data.get("is_official")
    ships_from_platform = request.data.get("ships_from_platform")
    admin_notes = request.data.get("admin_notes")

    if not seller_id:
        return Response({"detail": "Dados inválidos."}, status=status.HTTP_400_BAD_REQUEST)

    allowed_status = {
        Seller.Status.ACTIVE,
        Seller.Status.SUSPENDED,
        Seller.Status.PENDING,
        Seller.Status.REJECTED,
    }
    if new_status and new_status not in allowed_status:
        return Response({"detail": "Status inválido."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        seller = Seller.objects.get(pk=seller_id)
    except Seller.DoesNotExist:
        return Response({"detail": "Vendedor não encontrado."}, status=status.HTTP_404_NOT_FOUND)

    update_fields = ["updated_at"]
    if new_status:
        seller.status = new_status
        update_fields.append("status")
    if is_official is not None:
        if is_official:
            Seller.objects.filter(is_official=True).exclude(pk=seller.pk).update(is_official=False)
        seller.is_official = bool(is_official)
        update_fields.append("is_official")
    if ships_from_platform is not None:
        seller.ships_from_platform = bool(ships_from_platform)
        update_fields.append("ships_from_platform")
    if admin_notes is not None:
        seller.admin_notes = str(admin_notes)
        update_fields.append("admin_notes")

    seller.save(update_fields=update_fields)
    return Response({
        "ok": True,
        "id": seller.id,
        "status": seller.status,
        "is_official": seller.is_official,
        "ships_from_platform": seller.ships_from_platform,
    })


@api_view(["GET", "PATCH"])
@permission_classes([permissions.AllowAny])
def painel_payouts_api(request):
    if not painel_api_authorized(request):
        return Response({"detail": "Não autorizado."}, status=status.HTTP_403_FORBIDDEN)

    from api.models import SellerPayout, PayoutStatus
    from api.serializers.marketplace import SellerPayoutSerializer, PayoutProcessSerializer
    from api.services.payout_service import process_payout

    if request.method == "GET":
        status_filter = request.query_params.get("status", "").strip()
        qs = SellerPayout.objects.select_related("seller").order_by("-created_at")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response({"results": SellerPayoutSerializer(qs[:100], many=True).data})

    payout_id = request.data.get("id")
    ser = PayoutProcessSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        payout = SellerPayout.objects.get(pk=payout_id)
    except SellerPayout.DoesNotExist:
        return Response({"detail": "Repasse não encontrado."}, status=status.HTTP_404_NOT_FOUND)
    try:
        updated = process_payout(
            payout,
            ser.validated_data["status"],
            ser.validated_data.get("admin_notes", ""),
            ser.validated_data.get("payment_reference", ""),
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    if updated.status == 'paid':
        from api.services.notification_service import notify_payout_paid
        notify_payout_paid(updated.seller, updated)
    return Response(SellerPayoutSerializer(updated).data)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def painel_finance_api(request):
    if not painel_api_authorized(request):
        return Response({"detail": "Não autorizado."}, status=status.HTTP_403_FORBIDDEN)
    from api.services.finance_service import get_platform_finance_payload
    try:
        days = int(request.query_params.get("days", 30))
    except (TypeError, ValueError):
        days = 30
    return Response(get_platform_finance_payload(days=days))


@api_view(["GET", "PATCH"])
@permission_classes([permissions.AllowAny])
def painel_invoices_api(request):
    if not painel_api_authorized(request):
        return Response({"detail": "Não autorizado."}, status=status.HTTP_403_FORBIDDEN)

    from api.models import InvoiceRequest, InvoiceStatus
    from api.services.invoice_service import apply_invoice_update
    from api.utils import format_cnpj

    if request.method == "GET":
        status_filter = (request.query_params.get("status") or "").strip()
        qs = InvoiceRequest.objects.select_related("order", "user", "seller").order_by("-created_at")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response({
            "results": [
                {
                    "id": r.id,
                    "order_id": r.order_id,
                    "user_email": r.user.email,
                    "seller_name": r.seller.store_name if r.seller_id else "Galelugi Peças",
                    "cnpj": r.cnpj,
                    "cnpj_formatted": format_cnpj(r.cnpj),
                    "company_name": r.company_name,
                    "company_email": r.company_email,
                    "status": r.status,
                    "status_display": r.get_status_display(),
                    "invoice_number": r.invoice_number,
                    "invoice_url": r.invoice_url,
                    "nuvem_fiscal_id": r.nuvem_fiscal_id,
                    "nuvem_fiscal_status": r.nuvem_fiscal_status,
                    "nuvem_fiscal_chave": r.nuvem_fiscal_chave,
                    "admin_notes": r.admin_notes,
                    "created_at": r.created_at.isoformat(),
                }
                for r in qs[:100]
            ],
        })

    inv_id = request.data.get("id")
    try:
        inv = InvoiceRequest.objects.select_related("user").get(pk=inv_id)
    except InvoiceRequest.DoesNotExist:
        return Response({"detail": "Solicitação não encontrada."}, status=status.HTTP_404_NOT_FOUND)

    error = apply_invoice_update(inv, request.data)
    if error:
        return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"ok": True, "id": inv.id, "status": inv.status})
