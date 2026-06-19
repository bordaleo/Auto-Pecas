"""
URL configuration for Galelugi Peças.
"""
from django.urls import path, re_path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.shortcuts import redirect
from django.http import JsonResponse
from api.views.contact_views import build_whatsapp_url, normalize_whatsapp_phone, DEFAULT_MESSAGE
from api.models import SystemConfig
import os


def frontend_redirect(request, path=''):
    """Redireciona rotas da loja legada para o React (dev :3000)."""
    base = settings.FRONTEND_URL.rstrip('/')
    target = f'{base}/{path.lstrip("/")}' if path else base + '/'
    query = request.META.get('QUERY_STRING', '')
    if query:
        target = f'{target}?{query}'
    return redirect(target)


def payment_callback_view(request):
    if getattr(settings, 'SERVE_REACT_SPA', False):
        return redirect('/pedidos/')
    return redirect(f'{settings.FRONTEND_URL.rstrip("/")}/pedidos/')


def health_check_view(request):
    dist = getattr(settings, 'FRONTEND_DIST', None)
    index_ok = bool(dist and (dist / 'index.html').is_file())
    return JsonResponse({
        'status': 'ok',
        'serve_react_spa': getattr(settings, 'SERVE_REACT_SPA', False),
        'frontend_build': index_ok,
    })


def whatsapp_redirect_view(request):
    config = SystemConfig.get_config()
    phone = normalize_whatsapp_phone(config.store_whatsapp)
    message = request.GET.get('text') or DEFAULT_MESSAGE
    return redirect(build_whatsapp_url(phone, message))


static_dir = os.path.join(settings.BASE_DIR, 'static')
static_patterns = [
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': static_dir}),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('health/', health_check_view, name='health'),

    # WhatsApp (redirect externo)
    path('whatsapp/', whatsapp_redirect_view, name='whatsapp'),

    # Mercado Pago callbacks
    path('payment/success', payment_callback_view, name='payment_success'),
    path('payment/failure', payment_callback_view, name='payment_failure'),
    path('payment/pending', payment_callback_view, name='payment_pending'),
] + static_patterns

if getattr(settings, 'SERVE_REACT_SPA', False):
    from config.spa_views import serve_spa, serve_spa_asset

    urlpatterns += [
        re_path(r'^assets/(?P<path>.*)$', serve_spa_asset, name='spa-asset'),
        re_path(r'^(?!api/|admin/|static/|media/|whatsapp/|payment/).*$', serve_spa, name='spa'),
    ]
else:
    # Dev: loja React em :3000
    urlpatterns += [
        path('', lambda r: frontend_redirect(r), name='index'),
        path('pecas/', lambda r: frontend_redirect(r, 'pecas/'), name='catalog'),
        path('peca/<slug:slug>/', lambda r, slug: frontend_redirect(r, f'peca/{slug}/'), name='product'),
        path('carrinho/', lambda r: frontend_redirect(r, 'carrinho/'), name='cart'),
        path('checkout/', lambda r: frontend_redirect(r, 'checkout/'), name='checkout'),
        path('pedidos/', lambda r: frontend_redirect(r, 'pedidos/'), name='orders'),
        path('perfil/', lambda r: frontend_redirect(r, 'perfil/'), name='profile'),
        path('gerenciar/', lambda r: frontend_redirect(r, 'gerenciar/'), name='manage'),
        path('vender/', lambda r: frontend_redirect(r, 'vender/'), name='sell'),
        path('como-funciona/', lambda r: frontend_redirect(r, 'como-funciona/'), name='how-it-works'),
        path('faq-compatibilidade/', lambda r: frontend_redirect(r, 'faq-compatibilidade/'), name='faq-compatibilidade'),
        path('trocas-devolucoes/', lambda r: frontend_redirect(r, 'trocas-devolucoes/'), name='trocas-devolucoes'),
        path('prazos-entrega/', lambda r: frontend_redirect(r, 'prazos-entrega/'), name='prazos-entrega'),
        path('loja/<slug:slug>/', lambda r, slug: frontend_redirect(r, f'loja/{slug}/'), name='seller-store'),
        path('painel/', lambda r: frontend_redirect(r, 'painel/'), name='painel-root'),
        path('painel/entrar/', lambda r: frontend_redirect(r, 'painel/entrar/'), name='painel-entrar'),
        path('painel/sair/', lambda r: frontend_redirect(r, 'painel/entrar/'), name='painel-sair'),
        path('painel/visao/', lambda r: frontend_redirect(r, 'painel/visao/'), name='painel-visao'),
        path('painel/pedidos/', lambda r: frontend_redirect(r, 'painel/pedidos/'), name='painel-pedidos'),
        path('painel/pagamentos/', lambda r: frontend_redirect(r, 'painel/pagamentos/'), name='painel-pagamentos'),
        path('painel/conteudo/', lambda r: frontend_redirect(r, 'painel/conteudo/'), name='painel-conteudo'),
        path('painel/audiencia/', lambda r: frontend_redirect(r, 'painel/audiencia/'), name='painel-audiencia'),
        path('painel/config/', lambda r: frontend_redirect(r, 'painel/config/'), name='painel-config'),
        path('painel/erros/', lambda r: frontend_redirect(r, 'painel/erros/'), name='painel-erros'),
        path('painel/vendedores/', lambda r: frontend_redirect(r, 'painel/vendedores/'), name='painel-vendedores'),
        path('reset-password', lambda r: frontend_redirect(r, f'reset-password{("?" + r.META.get("QUERY_STRING")) if r.META.get("QUERY_STRING") else ""}'), name='reset_password_link'),
        path('verify-email', lambda r: frontend_redirect(r, f'verify-email{("?" + r.META.get("QUERY_STRING")) if r.META.get("QUERY_STRING") else ""}'), name='verify_email_link'),
        path('verify-email-change', lambda r: frontend_redirect(r, f'verify-email-change{("?" + r.META.get("QUERY_STRING")) if r.META.get("QUERY_STRING") else ""}'), name='verify_email_change_link'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
