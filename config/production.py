"""
Produção Galelugi — hosts, URLs e SPA definidos no código.

No Render, use DJANGO_SETTINGS_MODULE=config.production (automático via wsgi.py).
Não é necessário configurar ALLOWED_HOSTS, FRONTEND_URL, SERVE_REACT_SPA etc. no painel.
"""
import os

from config.settings import *  # noqa: F401,F403

DEBUG = False
SERVE_REACT_SPA = True

_SITE_HOSTS = (
    'galelugi.com.br',
    'www.galelugi.com.br',
    'galelugi.onrender.com',
)
_SITE_ORIGINS = (
    'https://galelugi.com.br',
    'https://www.galelugi.com.br',
    'https://galelugi.onrender.com',
)

ALLOWED_HOSTS = list(_SITE_HOSTS)
_render_host = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

_render_url = os.getenv('RENDER_EXTERNAL_URL', '').strip()
SITE_URL = _render_url or 'https://galelugi.onrender.com'
FRONTEND_URL = SITE_URL
BACKEND_URL = SITE_URL

CSRF_TRUSTED_ORIGINS = list(_SITE_ORIGINS)
if _render_url and _render_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_render_url)

CORS_ALLOWED_ORIGINS = list(_SITE_ORIGINS)
if _render_url and _render_url not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(_render_url)
CORS_ALLOW_ALL_ORIGINS = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
