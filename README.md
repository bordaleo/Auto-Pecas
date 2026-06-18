# AutoPeças Sandroni

Loja online de autopeças — Django + PostgreSQL + Mercado Pago + Brevo + Cloudinary.

## Rodar localmente

```bash
cd -site
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_sandroni
python manage.py createsuperuser
python manage.py runserver 8000
```

Acesse: http://localhost:8000

## Funcionalidades

- Catálogo com busca (nome, OEM, SKU, marca, veículo)
- Carrinho e checkout com Mercado Pago (PIX, cartão, boleto)
- Cadastro de peças em `/gerenciar/` (usuário staff)
- Django Admin em `/admin/`
- Painel operacional em `/painel/`

## Variáveis de ambiente (.env)

- `DATABASE_URL` — PostgreSQL
- `BREVO_API_KEY` + `SMTP_FROM_EMAIL` — emails
- `MERCADOPAGO_ACCESS_TOKEN` + `MERCADOPAGO_PUBLIC_KEY` — pagamentos
- `CLOUDINARY_*` — fotos de produtos

## Deploy

Ver `render.yaml` e `DEPLOY.md`.
