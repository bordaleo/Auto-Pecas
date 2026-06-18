# Deploy para Produção - Render (https://amorlize.onrender.com)

## Checklist de alterações feitas no código

1. **config/settings.py**
   - `ALLOWED_HOSTS` via variável de ambiente
   - `Whitenoise` no middleware para arquivos estáticos
   - `CORS_ALLOWED_ORIGINS` e `CSRF_TRUSTED_ORIGINS` via env
   - CORS em DEBUG permite todas as origens (dev)

2. **API_BASE_URL dinâmico**
   - `static/landing/app.js`, `static/app/script.js`, `static/app/edit.js`, `templates/admin/painel_*.html`
   - Usa `window.location.origin + '/api/v1'` (funciona em qualquer domínio)

3. **Rotas de pagamento**
   - `/payment/success`, `/payment/failure`, `/payment/pending` → redirecionam para `/?show=orders`

---

## PostgreSQL no Render

**Importante:** Crie um banco **PostgreSQL** no Render e **vincule** ao seu Web Service. O Render injeta automaticamente a variável `DATABASE_URL` com o host correto (não use 127.0.0.1).

1. No Render: **Dashboard** → **New** → **PostgreSQL**
2. Depois: no seu **Web Service** → **Settings** → **Environment** → **Add Environment Variable from Database** → selecione o banco

Se você configurou `DATABASE_URL` manualmente com valor local (127.0.0.1), remova e use a vinculação automática.

---

## Variáveis de ambiente no Render

Configure no **Dashboard do Render** → **Seu serviço** → **Environment**:

| Variável | Valor | Obrigatório |
|----------|-------|-------------|
| `SECRET_KEY` | Chave aleatória longa (ex: `openssl rand -hex 32`) | ✅ |
| `DEBUG` | `False` | ✅ |
| `ALLOWED_HOSTS` | `amorlize.onrender.com` | ✅ |
| `DATABASE_URL` | **Automático** – crie PostgreSQL e vincule ao serviço (não defina manualmente) | ✅ |
| `FRONTEND_URL` | `https://amorlize.onrender.com` | ✅ |
| `BACKEND_URL` | `https://amorlize.onrender.com` | ✅ |
| `CSRF_TRUSTED_ORIGINS` | `https://amorlize.onrender.com` | ✅ |
| `CORS_ALLOWED_ORIGINS` | `https://amorlize.onrender.com` | ✅ |
| `SMTP_HOST` | `smtp.gmail.com` | ✅ (para emails) |
| `SMTP_PORT` | `587` | ✅ |
| `SMTP_USER` | Seu email Gmail | ✅ |
| `SMTP_PASSWORD` | Senha de app do Gmail | ✅ |
| `SMTP_FROM_EMAIL` | Mesmo que SMTP_USER | ✅ |
| `MERCADOPAGO_ACCESS_TOKEN` | Token de **produção** do Mercado Pago | ✅ |
| `MERCADOPAGO_PUBLIC_KEY` | Public Key de **produção** (evita 401 na API de CEP do boleto) | ✅ em produção |
| `MERCADOPAGO_WEBHOOK_SECRET` | Webhook secret (opcional) | ⚠️ |
| `YOUTUBE_API_KEY` | Chave da API YouTube | ✅ |

No Render, defina também `SMTP_USER`, `SMTP_PASSWORD` e `SMTP_FROM_EMAIL` (e opcionalmente `SMTP_PORT=465` e `SMTP_USE_SSL=true` para Gmail com SSL). O backend usa timeout de 60s (`SMTP_TIMEOUT`) para conexões mais lentas.

---

## Mercado Pago – Webhook

No **Painel do Mercado Pago** → **Webhooks**, cadastre:

- **URL:** `https://amorlize.onrender.com/api/v1/payments/webhook`
- **Eventos:** Pagamentos

---

## Mercado Pago – Public Key em produção

A Public Key é injetada nos templates via variável de ambiente `MERCADOPAGO_PUBLIC_KEY`. Se não estiver definida, usa-se a chave de teste.

**No Render:** defina `MERCADOPAGO_PUBLIC_KEY` com a **Public Key de PRODUÇÃO** (em Desenvolvedores → Credenciais). Isso evita erro 401 na API de CEP ao usar boleto e garante que PIX/cartão funcionem em produção.

---

## Comandos de build e start no Render

- **Build Command:**  
  `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput`

- **Start Command:**  
  `gunicorn config.wsgi:application`

---

## Observações

1. **Render Free tier:** o serviço hiberna após ~15 min sem acesso. A primeira requisição pode demorar ~30–60 segundos.
2. **PostgreSQL:** crie um banco PostgreSQL no Render e use a `DATABASE_URL` gerada.
3. **Domínio próprio:** se usar ex.: `amorlize.com`, inclua em `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` e `CORS_ALLOWED_ORIGINS`.
