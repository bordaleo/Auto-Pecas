import re
from urllib.parse import quote

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import SystemConfig

DEFAULT_WHATSAPP = '5511974452478'
DEFAULT_MESSAGE = 'Olá! Gostaria de informações sobre peças automotivas.'


def normalize_whatsapp_phone(raw: str) -> str:
    digits = re.sub(r'\D', '', raw or '')
    if not digits:
        return DEFAULT_WHATSAPP
    if digits.startswith('55'):
        return digits
    if len(digits) in (10, 11):
        return f'55{digits}'
    return digits


def build_whatsapp_url(phone: str, message: str = DEFAULT_MESSAGE) -> str:
    return f'https://wa.me/{phone}?text={quote(message)}'


class WhatsAppContactView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        config = SystemConfig.get_config()
        raw = config.store_whatsapp or DEFAULT_WHATSAPP
        phone = normalize_whatsapp_phone(raw)
        message = request.query_params.get('text') or DEFAULT_MESSAGE
        display = raw or '(11) 97445-2478'
        return Response({
            'phone': phone,
            'display': display,
            'message': message,
            'url': build_whatsapp_url(phone, message),
        })
