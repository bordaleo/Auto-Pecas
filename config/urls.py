"""
URL configuration for AutoPeças Sandroni.
"""
from django.urls import path, re_path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.shortcuts import render, redirect
from api.views.contact_views import build_whatsapp_url, normalize_whatsapp_phone, DEFAULT_MESSAGE
from api.models import SystemConfig
from api.views.admin_views import (
    painel_audiencia,
    painel_conteudo,
    painel_config,
    painel_entrar,
    painel_erros,
    painel_pagamentos,
    painel_pedidos,
    painel_root_redirect,
    painel_sair,
    painel_visao,
)
import os


def sandroni_page(request, template_name):
    return render(request, f'sandroni/{template_name}')


def payment_callback_view(request):
    return redirect('/pedidos/')


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

    # Painel operacional
    path('painel/entrar/', painel_entrar, name='painel-entrar'),
    path('painel/sair/', painel_sair, name='painel-sair'),
    path('painel/visao/', painel_visao, name='painel-visao'),
    path('painel/pedidos/', painel_pedidos, name='painel-pedidos'),
    path('painel/pagamentos/', painel_pagamentos, name='painel-pagamentos'),
    path('painel/conteudo/', painel_conteudo, name='painel-conteudo'),
    path('painel/audiencia/', painel_audiencia, name='painel-audiencia'),
    path('painel/config/', painel_config, name='painel-config'),
    path('painel/erros/', painel_erros, name='painel-erros'),
    path('painel/', painel_root_redirect, name='painel-root'),

    # Loja AutoPeças Sandroni
    path('', lambda r: sandroni_page(r, 'index.html'), name='index'),
    path('pecas/', lambda r: sandroni_page(r, 'catalog.html'), name='catalog'),
    path('peca/<slug:slug>/', lambda r: sandroni_page(r, 'product.html'), name='product'),
    path('carrinho/', lambda r: sandroni_page(r, 'cart.html'), name='cart'),
    path('checkout/', lambda r: sandroni_page(r, 'checkout.html'), name='checkout'),
    path('pedidos/', lambda r: sandroni_page(r, 'orders.html'), name='orders'),
    path('perfil/', lambda r: sandroni_page(r, 'profile.html'), name='profile'),
    path('gerenciar/', lambda r: sandroni_page(r, 'manage.html'), name='manage'),
    path('whatsapp/', whatsapp_redirect_view, name='whatsapp'),

    # Auth links (processados via JS)
    path('reset-password', lambda r: sandroni_page(r, 'index.html'), name='reset_password_link'),
    path('verify-email', lambda r: sandroni_page(r, 'index.html'), name='verify_email_link'),
    path('verify-email-change', lambda r: sandroni_page(r, 'index.html'), name='verify_email_change_link'),

    # Mercado Pago callbacks
    path('payment/success', payment_callback_view, name='payment_success'),
    path('payment/failure', payment_callback_view, name='payment_failure'),
    path('payment/pending', payment_callback_view, name='payment_pending'),
] + static_patterns

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
