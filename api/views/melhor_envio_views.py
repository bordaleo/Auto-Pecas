from django.http import HttpResponseRedirect
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from api.services.melhor_envio_oauth_service import (
    exchange_code_for_token,
    melhor_envio_authorize_url,
    melhor_envio_redirect_uri,
    save_token_from_oauth,
)


class MelhorEnvioOAuthInfoView(APIView):
    """URLs e link de autorização para cadastro no Melhor Envio."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'redirect_uri': melhor_envio_redirect_uri(),
            'authorize_url': melhor_envio_authorize_url(),
            'hint': 'Use redirect_uri no cadastro do app Melhor Envio (Área Dev).',
        })


class MelhorEnvioOAuthCallbackView(APIView):
    """Callback OAuth — recebe ?code= e salva o token no SystemConfig."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        error = request.GET.get('error')
        if error:
            return HttpResponseRedirect(f'/painel/config/?melhor_envio=error&detail={error}')

        code = (request.GET.get('code') or '').strip()
        if not code:
            return HttpResponseRedirect('/painel/config/?melhor_envio=missing_code')

        try:
            payload = exchange_code_for_token(code)
            save_token_from_oauth(payload)
            return HttpResponseRedirect('/painel/config/?melhor_envio=connected')
        except ValueError as exc:
            from urllib.parse import quote
            return HttpResponseRedirect(f'/painel/config/?melhor_envio=error&detail={quote(str(exc))}')
