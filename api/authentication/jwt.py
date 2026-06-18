import jwt
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions
from rest_framework.authentication import BaseAuthentication

User = get_user_model()


class JWTAuthentication(BaseAuthentication):
    """Autenticação JWT customizada para Django REST Framework"""
    
    def authenticate(self, request):
        """Autentica o usuário baseado no token JWT"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            email = payload.get('sub')
            
            if not email:
                raise exceptions.AuthenticationFailed('Token inválido')
            
            try:
                user = User.objects.get(email=email, is_active=True)
            except User.DoesNotExist:
                raise exceptions.AuthenticationFailed('Usuário não encontrado')
            
            return (user, token)
            
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Sua sessão expirou. Faça login novamente.')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Sua sessão expirou. Faça login novamente.')
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Erro de autenticação: {str(e)}')


def create_access_token(user, expires_delta=None):
    """Cria um token JWT para o usuário"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        'sub': user.email,
        'exp': expire,
        'iat': datetime.utcnow(),
        'user_id': user.id,
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_access_token(token):
    """Decodifica e valida um token JWT"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
