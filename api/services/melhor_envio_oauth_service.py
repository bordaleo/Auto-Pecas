"""OAuth2 Melhor Envio — troca code por token e persiste no SystemConfig."""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from api.models import SystemConfig
from config.secrets import cfg

logger = logging.getLogger(__name__)

AUTH_SANDBOX = 'https://sandbox.melhorenvio.com.br/oauth/token'
AUTH_PROD = 'https://melhorenvio.com.br/oauth/token'


def melhor_envio_redirect_uri() -> str:
    base = (
        (cfg('MELHOR_ENVIO_CALLBACK_BASE', '') or '').strip()
        or (cfg('BACKEND_URL', '') or '').strip()
        or getattr(settings, 'BACKEND_URL', None)
        or getattr(settings, 'SITE_URL', None)
        or getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
    ).rstrip('/')
    return f'{base}/api/v1/integrations/melhor-envio/callback/'


def melhor_envio_authorize_url(scopes: str | None = None) -> str | None:
    client_id = (cfg('MELHOR_ENVIO_CLIENT_ID', '') or '').strip()
    if not client_id:
        return None
    config = SystemConfig.get_config()
    base = 'https://sandbox.melhorenvio.com.br' if config.melhor_envio_sandbox else 'https://melhorenvio.com.br'
    scope = scopes or 'shipping-calculate shipping-companies cart-read cart-write'
    from urllib.parse import urlencode
    params = urlencode({
        'client_id': client_id,
        'redirect_uri': melhor_envio_redirect_uri(),
        'response_type': 'code',
        'state': 'galelugi',
        'scope': scope,
    })
    return f'{base}/oauth/authorize?{params}'


def exchange_code_for_token(code: str) -> dict:
    client_id = (cfg('MELHOR_ENVIO_CLIENT_ID', '') or '').strip()
    client_secret = (cfg('MELHOR_ENVIO_CLIENT_SECRET', '') or '').strip()
    if not client_id or not client_secret:
        raise ValueError('MELHOR_ENVIO_CLIENT_ID e MELHOR_ENVIO_CLIENT_SECRET não configurados.')

    config = SystemConfig.get_config()
    url = AUTH_SANDBOX if config.melhor_envio_sandbox else AUTH_PROD
    payload = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': melhor_envio_redirect_uri(),
        'code': code,
    }
    resp = requests.post(
        url,
        json=payload,
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Galelugi Pecas (contato@galelugi.com.br)',
        },
        timeout=20,
    )
    if resp.status_code != 200:
        logger.warning('Melhor Envio token HTTP %s: %s', resp.status_code, resp.text[:400])
        raise ValueError('Não foi possível obter o token do Melhor Envio. Verifique Client ID, Secret e callback URL.')
    return resp.json()


def save_token_from_oauth(payload: dict) -> str:
    token = (payload.get('access_token') or '').strip()
    if not token:
        raise ValueError('Resposta do Melhor Envio sem access_token.')
    config = SystemConfig.get_config()
    config.melhor_envio_token = token
    config.save(update_fields=['melhor_envio_token', 'updated_at'])
    return token
