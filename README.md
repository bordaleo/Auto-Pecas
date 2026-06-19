# Galelugi Peças

Marketplace de autopeças inspirado no [Mercado Livre](https://www.mercadolivre.com.br/) — React + Node.js (frontend) e Django (API).

## Stack

| Camada | Tecnologia |
|--------|------------|
| Frontend | React 19 + Vite + React Router |
| Servidor Node | Express (proxy API + static em produção) |
| Backend | Django REST API + PostgreSQL + Mercado Pago |

## Rodar localmente

### 1. Backend (Django)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_sandroni
python manage.py runserver
```

API em: http://127.0.0.1:8000/api/v1/

### 2. Frontend (React)

```bash
npm run install:all
npm run dev
```

Loja em: http://127.0.0.1:3000

### Rodar tudo junto

```bash
npm run install:all
npm run dev:all
```

## Produção

```bash
npm run build
npm run start --prefix server
```

O servidor Node na porta 3000 serve o React e faz proxy de `/api` para o Django.

## Funcionalidades

- Catálogo com busca (nome, OEM, SKU, marca, veículo)
- Carrinho, checkout com Mercado Pago (PIX, cartão, boleto)
- Frete por CEP ou retirada na loja
- Conta de usuário, pedidos, painel admin de peças
- Design inspirado no Mercado Livre (header amarelo, busca central, cards de produto)

## Variáveis de ambiente

- `DATABASE_URL` — PostgreSQL (obrigatório)
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `MERCADOPAGO_ACCESS_TOKEN` + `MERCADOPAGO_PUBLIC_KEY` — pagamentos
- `FRONTEND_URL` — padrão `http://localhost:3000`
- `CORS_ALLOWED_ORIGINS` — incluir origem do React
