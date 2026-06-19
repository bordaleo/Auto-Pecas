"""
Modelo de segredos — NÃO commite credentials.py (GitHub bloqueia chaves).

Local:
    cp config/credentials.example.py config/credentials.py
    # ou: python scripts/sync_credentials.py  (lê o .env)

Produção (Render): configure só os segredos no Environment do serviço
(SECRET_KEY, MERCADOPAGO_*, CLOUDINARY_*, SMTP_*, BREVO_API_KEY).
Hosts, URLs e SPA ficam em config/production.py — não precisa no painel.
"""

SECRET_KEY = 'troque-por-uma-chave-longa-e-aleatoria'

MERCADOPAGO_ACCESS_TOKEN = ''
MERCADOPAGO_PUBLIC_KEY = ''
MERCADOPAGO_WEBHOOK_SECRET = ''

CLOUDINARY_CLOUD_NAME = ''
CLOUDINARY_API_KEY = ''
CLOUDINARY_API_SECRET = ''

SMTP_HOST = 'smtp-relay.brevo.com'
SMTP_PORT = 465
SMTP_USER = ''
SMTP_PASSWORD = ''
SMTP_FROM_EMAIL = ''
SMTP_USE_SSL = True

BREVO_API_KEY = ''

PAINEL_GATE_PASSWORD = 'troque-esta-senha'
