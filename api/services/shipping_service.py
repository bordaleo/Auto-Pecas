import re
from decimal import Decimal

from api.models import DeliveryMethod, SystemConfig

DEFAULT_PICKUP_ADDRESS = 'Rua São Sabino, 262'


def normalize_zip(zip_code):
    return re.sub(r'\D', '', zip_code or '')


def get_pickup_address():
    config = SystemConfig.get_config()
    return (config.store_address or DEFAULT_PICKUP_ADDRESS).strip()


def calculate_shipping_fee(delivery_method, subtotal, zip_code=None):
    """
    Calcula frete da loja.
    - Retirada na loja: grátis
    - Entrega: grátis acima do mínimo configurado; senão por região do CEP
    """
    subtotal = Decimal(str(subtotal or '0'))
    config = SystemConfig.get_config()
    free_min = config.free_shipping_min or Decimal('299.00')

    if delivery_method == DeliveryMethod.PICKUP:
        return Decimal('0.00'), True, get_pickup_address()

    if subtotal >= free_min:
        return Decimal('0.00'), True, get_pickup_address()

    zip_digits = normalize_zip(zip_code)
    if len(zip_digits) != 8:
        return None, False, get_pickup_address()

    prefix = int(zip_digits[:2])
    if prefix <= 19:
        fee = Decimal('19.90')
    elif prefix <= 39:
        fee = Decimal('39.90')
    else:
        fee = Decimal('59.90')

    return fee, False, get_pickup_address()
