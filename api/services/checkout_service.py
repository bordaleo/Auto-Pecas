"""Checkout multi-vendedor: frete e pedido por loja."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from api.models import Order, OrderGroup, OrderItem, OrderStatus, DeliveryMethod, Seller
from api.services.marketplace_service import split_sale_amount
from api.services.melhor_envio_service import calculate_shipping_with_provider
from api.services.shipping_origin import resolve_shipping_origin
from api.services.shipping_service import get_pickup_address
from api.services.stock_reservation_service import (
    get_available_stock, create_reservations_for_order,
)


def _seller_key(seller) -> str:
    return str(seller.id) if seller else 'platform'


def group_cart_items(order_items_data: list[dict]) -> dict[str, list]:
    groups = defaultdict(list)
    for item in order_items_data:
        groups[_seller_key(item['seller'])].append(item)
    return groups


def calculate_group_shipping(delivery_method, zip_code, group_items: list[dict], subtotal: Decimal):
    seller = group_items[0].get('seller') if group_items else None
    origin_zip, _, _ = resolve_shipping_origin(seller)
    me_cart = [
        {
            'price': float(i['unit_price']),
            'quantity': i['quantity'],
            'weight_kg': float(i.get('weight_kg') or 1),
            'width_cm': i.get('width_cm') or 20,
            'height_cm': i.get('height_cm') or 10,
            'length_cm': i.get('length_cm') or 30,
        }
        for i in group_items
    ]
    return calculate_shipping_with_provider(
        delivery_method, subtotal, zip_code, cart_items=me_cart, origin_zip=origin_zip,
    )


@transaction.atomic
def create_orders_from_cart(user, data, order_items_data: list[dict], discount_amount, coupon_code):
    """
    Cria OrderGroup + um Order por vendedor (ou Galelugi).
    Retorna (order_group, orders_list, primary_order).
    """
    delivery_method = data.get('delivery_method', DeliveryMethod.DELIVERY)
    shipping_zip = data.get('shipping_zip', '')
    groups = group_cart_items(order_items_data)

    subtotal_all = sum(
        i['unit_price'] * i['quantity'] for i in order_items_data
    )

    shipping_parts = []
    for key, items in groups.items():
        group_sub = sum(i['unit_price'] * i['quantity'] for i in items)
        fee, _, _, meta = calculate_group_shipping(delivery_method, shipping_zip, items, group_sub)
        if fee is None:
            raise ValueError('CEP inválido para calcular o frete.')
        shipping_parts.append((key, items, fee, meta, group_sub))

    total_shipping = sum(p[2] for p in shipping_parts)
    total = subtotal_all + total_shipping - discount_amount
    total = max(Decimal('0.01'), total)

    order_group = OrderGroup.objects.create(
        user=user,
        status=OrderStatus.PENDING,
        amount=total,
        discount_amount=discount_amount,
        coupon_code=coupon_code or '',
    )

    pickup_address = get_pickup_address()
    shipping_address = data.get('shipping_address', '')
    shipping_city = data.get('shipping_city', '')
    shipping_state = data.get('shipping_state', '')

    if delivery_method == DeliveryMethod.PICKUP:
        shipping_address = pickup_address
        shipping_city = shipping_city or 'Retirada na loja'
        shipping_state = shipping_state or 'SP'
        shipping_zip = shipping_zip or ''

    orders_created = []
    for key, items, shipping_fee, ship_meta, group_sub in shipping_parts:
        seller = items[0]['seller'] if key != 'platform' else None
        order_amount = group_sub + shipping_fee
        if discount_amount > 0 and subtotal_all > 0:
            share = group_sub / subtotal_all
            order_amount = max(Decimal('0.01'), order_amount - (discount_amount * share))

        order = Order.objects.create(
            user=user,
            order_group=order_group,
            fulfillment_seller=seller,
            status=OrderStatus.PENDING,
            amount=order_amount.quantize(Decimal('0.01')),
            shipping_fee=shipping_fee,
            shipping_service_name=ship_meta.get('service_name', ''),
            shipping_days=ship_meta.get('days'),
            shipping_provider=ship_meta.get('provider', 'fixed'),
            delivery_method=delivery_method,
            discount_amount=Decimal('0.00'),
            coupon_code=coupon_code or '',
            order_email=data.get('order_email') or user.email,
            customer_name=data['customer_name'],
            customer_phone=data.get('customer_phone', ''),
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_state=shipping_state,
            shipping_zip=shipping_zip,
            notes=data.get('notes', ''),
        )

        reservation_items = []
        for item_data in items:
            OrderItem.objects.create(order=order, **{
                k: v for k, v in item_data.items()
                if k not in ('weight_kg', 'width_cm', 'height_cm')
            })
            reservation_items.append({
                'product': item_data['product'],
                'quantity': item_data['quantity'],
            })
        create_reservations_for_order(order, user, reservation_items)
        orders_created.append(order)

    return order_group, orders_created, orders_created[0]


def build_order_items_from_request(data, user):
    """Valida carrinho e monta order_items_data."""
    order_items_data = []
    for item in data['items']:
        from api.models import Product
        product = Product.objects.select_for_update().get(
            id=item['product_id'], is_active=True,
        )
        qty = item['quantity']
        available = get_available_stock(product)
        if available < qty:
            raise ValueError(
                f'Estoque insuficiente para "{product.name}". Disponível: {available}.'
            )
        line_gross = product.price * qty
        platform_fee, seller_earning, _ = split_sale_amount(line_gross, product.seller)
        order_items_data.append({
            'product': product,
            'seller': product.seller,
            'product_name': product.name,
            'product_sku': product.sku,
            'unit_price': product.price,
            'quantity': qty,
            'image_url': product.image_url,
            'platform_fee': platform_fee,
            'seller_earning': seller_earning,
            'weight_kg': product.weight_kg,
            'width_cm': product.width_cm,
            'height_cm': product.height_cm,
            'length_cm': product.length_cm,
        })
    return order_items_data
