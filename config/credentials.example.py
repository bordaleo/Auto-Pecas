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

# Nuvem Fiscal — NF-e (https://console.nuvemfiscal.com.br)
NUVEM_FISCAL_CLIENT_ID = ''
NUVEM_FISCAL_CLIENT_SECRET = ''
NUVEM_FISCAL_SANDBOX = True
NUVEM_FISCAL_EMITTER_CNPJ = ''
NUVEM_FISCAL_EMITTER_CPF = ''
NUVEM_FISCAL_EMITTER_UF = 'SP'
NUVEM_FISCAL_EMITTER_CITY_IBGE = '3550308'
NUVEM_FISCAL_DEFAULT_NCM = '87089990'
NUVEM_FISCAL_CRT = '1'
NUVEM_FISCAL_CFOP = '5102'
NUVEM_FISCAL_MOCK = False

# Melhor Envio — frete (https://docs.melhorenvio.com.br)
# Após criar o app na Área Dev, use as URLs abaixo no cadastro (HTTPS obrigatório).
# Callback: {BACKEND_URL}/api/v1/integrations/melhor-envio/callback/
MELHOR_ENVIO_CLIENT_ID = ''
MELHOR_ENVIO_CLIENT_SECRET = ''
MELHOR_ENVIO_TOKEN = ''
MELHOR_ENVIO_CALLBACK_BASE = 'https://galelugi.onrender.com'
