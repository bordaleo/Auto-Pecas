"""Pedidos de peça — matching, expiração, proximidade e sugestões."""
from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.utils import timezone

from api.models import (
    PartRequest, PartRequestConversation, PartRequestRating, PartRequestStatus,
    Product, ProductVehicleCompatibility, Seller,
)
from api.services.vin_lookup_service import decode_vin, lookup_plate, parse_vehicle_text_query

MAX_OPEN_REQUESTS = 3
EXPIRY_DAYS = 14
STOP_WORDS = frozenset({
    'preciso', 'precisamos', 'peça', 'peca', 'peças', 'pecas', 'para', 'com', 'uma', 'um', 'de', 'do', 'da',
    'nos', 'na', 'no', 'em', 'ou', 'e', 'gol', 'carro', 'veículo', 'veiculo', 'modelo', 'ano',
})

QUOTE_CONDITION_LABELS = {
    'new': 'Nova',
    'used': 'Usada',
    'reconditioned': 'Recondicionada',
}


def _normalize_zip(value: str) -> str:
    return re.sub(r'\D', '', (value or ''))[:8]


def zip_proximity_score(seller_zip: str, requester_zip: str) -> int:
    """Score 0–100: CEPs mais próximos pontuam mais."""
    a, b = _normalize_zip(seller_zip), _normalize_zip(requester_zip)
    if not a or not b:
        return 0
    if a[:5] == b[:5]:
        return 100
    if a[:3] == b[:3]:
        return 60
    if a[:2] == b[:2]:
        return 30
    return 0


def _keywords(text: str) -> list[str]:
    words = re.findall(r'[a-zA-Z0-9]+', (text or '').lower())
    return [w for w in words if len(w) >= 4 and w not in STOP_WORDS][:8]


def seller_match_score(seller: Seller, part_request: PartRequest) -> int:
    """0–100: quanto o estoque do vendedor combina com o pedido."""
    products = Product.objects.filter(seller=seller, is_active=True)
    if not products.exists():
        return 0

    score = 0

    if part_request.vehicle_model_ref_id:
        if products.filter(vehicle_compatibilities__vehicle_model_id=part_request.vehicle_model_ref_id).exists():
            score += 50

    if part_request.vehicle_brand:
        brand = part_request.vehicle_brand.strip()
        if products.filter(
            Q(vehicle_compatibilities__vehicle_model__brand__name__icontains=brand)
            | Q(compatible_vehicles__icontains=brand)
        ).exists():
            score += 20

    if part_request.vehicle_model:
        token = part_request.vehicle_model.strip().split()[0]
        if len(token) >= 3 and products.filter(
            Q(vehicle_compatibilities__vehicle_model__name__icontains=token)
            | Q(name__icontains=token)
            | Q(compatible_vehicles__icontains=token)
        ).exists():
            score += 20

    for kw in _keywords(part_request.description):
        if products.filter(
            Q(name__icontains=kw) | Q(oem_code__icontains=kw) | Q(description__icontains=kw)
        ).exists():
            score += 10
            break

    return min(score, 100)


def find_matching_sellers(part_request: PartRequest):
    """Vendedores com estoque compatível; fallback para todos os ativos."""
    sellers = list(
        Seller.objects.filter(status=Seller.Status.ACTIVE)
        .exclude(user_id=part_request.requester_id)
        .select_related('user'),
    )
    if not sellers:
        return Seller.objects.none()

    scored = [(s, seller_match_score(s, part_request)) for s in sellers]
    matched = [s for s, sc in scored if sc >= 20]
    if matched:
        return Seller.objects.filter(id__in=[s.id for s in matched])
    return Seller.objects.filter(id__in=[s.id for s in sellers])


def enrich_vehicle_from_lookup(part_request: PartRequest, *, plate: str = '', vin: str = '', query: str = '', year=None):
    """Preenche campos veiculares a partir de placa/VIN/texto."""
    if plate:
        result = lookup_plate(plate, year_override=year)
    elif vin:
        result = decode_vin(vin, year_override=year)
    elif query:
        result = parse_vehicle_text_query(query, year_override=year)
    else:
        return part_request

    if not result.get('valid'):
        return part_request

    if result.get('brand_hint') and not part_request.vehicle_brand:
        part_request.vehicle_brand = result['brand_hint']
    if result.get('model_hint') and not part_request.vehicle_model:
        part_request.vehicle_model = result['model_hint']
    if result.get('year_hint') and not part_request.vehicle_year:
        part_request.vehicle_year = result['year_hint']

    models = result.get('vehicle_models') or []
    if models and not part_request.vehicle_model_ref_id:
        part_request.vehicle_model_ref_id = models[0]['id']

    return part_request


def expire_old_part_requests() -> int:
    """Encerra pedidos abertos há mais de EXPIRY_DAYS dias."""
    cutoff = timezone.now() - timedelta(days=EXPIRY_DAYS)
    qs = PartRequest.objects.filter(status=PartRequestStatus.OPEN, created_at__lt=cutoff)
    count = qs.count()
    if count:
        qs.update(status=PartRequestStatus.CLOSED, closed_at=timezone.now())
    return count


def count_open_requests(user) -> int:
    return PartRequest.objects.filter(requester=user, status=PartRequestStatus.OPEN).count()


def sort_requests_for_seller(requests: list[dict], seller: Seller) -> list[dict]:
    """Ordena pedidos: não respondidos, match + proximidade, mais recentes."""
    seller_zip = seller.origin_zip or seller.user.shipping_zip or ''

    def sort_key(item):
        match = item.get('match_score') or 0
        prox = zip_proximity_score(seller_zip, item.get('requester_zip') or '')
        unresponded = 0 if item.get('already_responded') else 1
        created_ts = item.get('created_at') or ''
        return (unresponded, match + prox, created_ts)

    return sorted(requests, key=sort_key, reverse=True)


def build_quote_message(conv: PartRequestConversation, seller: Seller) -> str:
    """Monta mensagem estruturada de orçamento."""
    req = conv.part_request
    lines = [f'Orçamento — {seller.store_name}', f'Pedido: {req.description[:200]}']
    if conv.quote_price is not None:
        lines.append(f'Preço: R$ {conv.quote_price:.2f}'.replace('.', ','))
    if conv.quote_condition:
        lines.append(f'Condição: {QUOTE_CONDITION_LABELS.get(conv.quote_condition, conv.quote_condition)}')
    if conv.quote_delivery_days:
        lines.append(f'Prazo: {conv.quote_delivery_days} dia(s) úteis')
    if conv.quote_product_id:
        product = conv.quote_product
        if not product:
            from api.models import Product
            product = Product.objects.filter(pk=conv.quote_product_id).first()
        if product:
            base = getattr(settings, 'FRONTEND_URL', 'http://127.0.0.1:5173').rstrip('/')
            lines.append(f'Peça no catálogo: {base}/peca/{product.slug}/')
    if conv.quote_notes:
        lines.append(conv.quote_notes.strip())
    return '\n'.join(lines)


def build_whatsapp_url_for_request(conv: PartRequestConversation, seller: Seller) -> str:
    req = conv.part_request
    phone = ''
    if req.show_phone:
        phone = (req.contact_phone or '').strip() or (req.requester.phone or '').strip()
    digits = ''.join(c for c in phone if c.isdigit())
    if not digits:
        return ''
    if not digits.startswith('55'):
        digits = '55' + digits.lstrip('0')

    vehicle = ' '.join(filter(None, [req.vehicle_brand, req.vehicle_model, str(req.vehicle_year or '')]))
    text = (
        f'Olá {req.requester.name}! Sou da {seller.store_name} na Galelugi. '
        f'Vi seu pedido: "{req.description[:120]}"'
    )
    if vehicle.strip():
        text += f' ({vehicle.strip()})'
    if conv.quote_price is not None:
        text += f'. Posso oferecer por R$ {conv.quote_price:.2f}'.replace('.', ',')
    text += '. Podemos conversar?'
    return f'https://wa.me/{digits}?text={quote(text)}'


def suggest_products(q: str = '', vehicle_brand: str = '', vehicle_model: str = '', vehicle_year: str = '', limit: int = 6):
    """Sugere peças similares antes de criar pedido."""
    from api.services.product_search_service import (
        apply_text_search,
        apply_vehicle_brand_filter,
        apply_vehicle_model_filter,
        apply_vehicle_year_filter,
    )

    qs = Product.objects.filter(is_active=True).select_related('category', 'seller')
    if q:
        qs = apply_text_search(qs, q)
    if vehicle_brand:
        qs = apply_vehicle_brand_filter(qs, vehicle_brand)
    if vehicle_model:
        qs = apply_vehicle_model_filter(qs, vehicle_model)
    if vehicle_year:
        qs = apply_vehicle_year_filter(qs, vehicle_year)
    return list(qs.distinct().order_by('-is_featured', '-stock')[:limit])


def get_seller_part_request_stats(seller: Seller) -> dict:
    expire_old_part_requests()
    open_qs = PartRequest.objects.filter(status=PartRequestStatus.OPEN).exclude(requester_id=seller.user_id)
    open_count = open_qs.count()
    responded_ids = set(
        PartRequestConversation.objects.filter(
            seller=seller, part_request__status=PartRequestStatus.OPEN,
        ).values_list('part_request_id', flat=True),
    )
    unresponded_count = open_qs.exclude(id__in=responded_ids).count()
    ratings = PartRequestRating.objects.filter(conversation__seller=seller).aggregate(
        avg=Avg('rating'), count=Count('id'),
    )
    return {
        'open_count': open_count,
        'unresponded_count': unresponded_count,
        'avg_rating': round(float(ratings['avg'] or 0), 1),
        'rating_count': ratings['count'] or 0,
    }


def get_part_request_admin_metrics(days: int = 30) -> dict:
    since = timezone.now() - timedelta(days=days)
    qs = PartRequest.objects.filter(created_at__gte=since)
    total = qs.count()
    open_count = qs.filter(status=PartRequestStatus.OPEN).count()
    fulfilled = qs.filter(status=PartRequestStatus.FULFILLED).count()
    closed = qs.filter(status=PartRequestStatus.CLOSED).count()
    conversations = PartRequestConversation.objects.filter(created_at__gte=since).count()
    ratings = PartRequestRating.objects.filter(created_at__gte=since).aggregate(avg=Avg('rating'))
    avg_response_hours = None
    convs = PartRequestConversation.objects.filter(created_at__gte=since).select_related('part_request')
    if convs.exists():
        deltas = []
        for c in convs[:200]:
            delta = (c.created_at - c.part_request.created_at).total_seconds() / 3600
            if delta >= 0:
                deltas.append(delta)
        if deltas:
            avg_response_hours = round(sum(deltas) / len(deltas), 1)

    return {
        'period_days': days,
        'total': total,
        'open': open_count,
        'fulfilled': fulfilled,
        'closed': closed,
        'conversations': conversations,
        'fulfillment_rate': round(fulfilled / total * 100, 1) if total else 0,
        'avg_rating': round(float(ratings['avg'] or 0), 1),
        'avg_first_response_hours': avg_response_hours,
    }
