from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle


class AuthLoginThrottle(AnonRateThrottle):
    scope = 'auth_login'


class AuthRegisterThrottle(AnonRateThrottle):
    scope = 'auth_register'


class AuthPasswordThrottle(AnonRateThrottle):
    """Forgot / reset password — limita envio de códigos por IP."""
    scope = 'auth_password'


class AuthVerifyThrottle(AnonRateThrottle):
    """Verificação de email e códigos OTP."""
    scope = 'auth_verify'


class AuthEmailTargetThrottle(SimpleRateThrottle):
    """Limita tentativas por endereço de email (além do limite por IP)."""
    scope = 'auth_email_target'

    def get_cache_key(self, request, view):
        email = ''
        if request.method == 'POST' and isinstance(getattr(request, 'data', None), dict):
            email = (request.data.get('email') or '').strip().lower()
        if not email:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': email}
