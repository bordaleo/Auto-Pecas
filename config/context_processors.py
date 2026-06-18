"""
Context processors para templates Django.
"""
from django.conf import settings


def site_domain(request):
    """Injeta SITE_DOMAIN em todos os templates (host atual ou fallback de produção)."""
    return {
        'SITE_DOMAIN': request.get_host() if request else 'autopecassandroni.com.br',
    }


def mercadopago_public_key(request):
    """Injeta MERCADOPAGO_PUBLIC_KEY para os Bricks. Use chave de PRODUÇÃO em produção (evita 401 na API de CEP do boleto)."""
    return {
        'mercadopago_public_key': getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', '') or 'TEST-52b8b435-fb3a-4793-b8f4-fe5a261260e7',
    }
