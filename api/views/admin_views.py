import json
import logging
import secrets
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from api.authentication.jwt import decode_access_token
from api.models import OpsAlertEvent, SystemConfig

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
    from api.serializers.system_config import SystemConfigPublicSerializer
    config = SystemConfig.get_config()
    return Response(SystemConfigPublicSerializer(config).data)


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
