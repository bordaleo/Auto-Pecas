from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import random
from api.models import User, PasswordResetToken, AccountVerificationToken, EmailChangeToken
from api.serializers import (
    UserRegisterSerializer,
    UserResponseSerializer,
    UserUpdateSerializer,
    LoginSerializer,
    TokenSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    MessageSerializer,
    VerifyEmailSerializer,
    ResendVerificationEmailSerializer
)
from api.authentication.jwt import create_access_token
from api.services.email_service import email_service
from django.conf import settings

logger = __import__('logging').getLogger(__name__)


def generate_unique_verification_code(model_class, length=6, max_retries=20):
    """Gera um código numérico único para o model informado."""
    for _ in range(max_retries):
        code = ''.join(str(random.randint(0, 9)) for _ in range(length))
        if not model_class.objects.filter(token=code).exists():
            return code
    raise Exception("Não foi possível gerar um código de verificação único")


class RegisterView(APIView):
    """View para registro de novo usuário"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            # Log dos dados recebidos (sem senha)
            logger.info(f"Tentativa de registro recebida. Email: {request.data.get('email', 'N/A')}, Nome: {request.data.get('name', 'N/A')}")
            
            serializer = UserRegisterSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    user = serializer.save()  # Usuário criado com is_active=False
                    logger.info(f"Usuário criado com sucesso: {user.email} (ID: {user.id})")
                    
                    # Invalida tokens anteriores não usados do usuário
                    AccountVerificationToken.objects.filter(
                        user=user,
                        used=False,
                        expires_at__gt=timezone.now()
                    ).update(used=True)
                    
                    # Gera novo código de verificação (com retry em caso de colisão)
                    max_retries = 5
                    verification_token = None
                    code = None
                    for attempt in range(max_retries):
                        try:
                            code = generate_unique_verification_code(AccountVerificationToken)
                            expire_hours = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRE_HOURS', 24)  # Usa mesma expiração
                            expires_at = timezone.now() + timedelta(hours=expire_hours)
                            
                            # Cria registro do código
                            verification_token = AccountVerificationToken.objects.create(
                                user=user,
                                token=code,
                                used=False,
                                expires_at=expires_at
                            )
                            logger.info(f"Código de verificação criado com sucesso para {user.email}")
                            break
                        except Exception as e:
                            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                                logger.warning(f"Colisão de código detectada (tentativa {attempt + 1}/{max_retries}), tentando novamente...")
                                if attempt == max_retries - 1:
                                    raise Exception("Não foi possível gerar um código único após várias tentativas")
                                continue
                            else:
                                raise
                    
                    # Verifica se o código foi criado com sucesso
                    if not verification_token or not code:
                        raise Exception("Falha ao criar código de verificação")
                    
                    # Envia email de verificação
                    try:
                        email_service.send_verification_email(
                            to_email=user.email,
                            verification_code=code,
                            user_name=user.name
                        )
                        logger.info(f"Email de verificação enviado para {user.email}")
                    except Exception as e:
                        logger.error(f"Erro ao enviar email de verificação: {e}", exc_info=True)
                        # Não falha o registro se o email não for enviado
                    
                    response_data = {
                        "message": (
                            "Conta criada! Você já pode usar a loja."
                            if user.is_active
                            else (
                                "Encontramos uma conta pendente para este e-mail e enviamos um novo código."
                                if serializer.context.get('reused_inactive_user')
                                else "Conta criada! Verifique seu email para ativar."
                            )
                        ),
                        "user": UserResponseSerializer(user).data,
                        "verified": user.is_active,
                    }
                    if user.is_active:
                        response_data["access_token"] = create_access_token(user)
                        response_data["token_type"] = "bearer"

                    return Response(response_data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    error_msg = str(e)
                    # Email duplicado: esperado — não dispara alerta operacional
                    if 'unique' in error_msg.lower() or 'duplicate' in error_msg.lower():
                        if 'email' in error_msg.lower():
                            logger.warning(f"Registro: email já cadastrado ({e})")
                            return Response(
                                {"detail": "Este email já está cadastrado."},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    logger.error(f"Erro ao criar usuário: {e}", exc_info=True)
                    return Response(
                        {"detail": f"Erro ao criar conta: {error_msg}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Formata erros do serializer em uma mensagem legível
            logger.warning(f"Erros de validação no registro: {serializer.errors}")
            error_messages = []
            for field, errors in serializer.errors.items():
                if isinstance(errors, list):
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                else:
                    error_messages.append(f"{field}: {errors}")
            
            error_detail = "; ".join(error_messages) if error_messages else "Erro ao criar conta. Verifique os dados informados."
            return Response(
                {"detail": error_detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Erro inesperado no registro: {e}", exc_info=True)
            return Response(
                {"detail": "Erro ao criar conta. Tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(APIView):
    """View para login - retorna token JWT"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Login falhou - Erros de validação: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        # Normaliza o email usando o mesmo método do UserManager
        email = User.objects.normalize_email(email)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"Login falhou - Usuário não encontrado: {email}")
            return Response(
                {"detail": "Email ou senha incorretos"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.check_password(password):
            logger.warning(f"Login falhou - Senha incorreta para usuário: {email}")
            return Response(
                {"detail": "Email ou senha incorretos"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            logger.warning(f"Login falhou - Usuário não verificado: {email}")
            return Response(
                {"detail": "Sua conta ainda não foi verificada. Verifique seu email e informe o código de verificação para ativar sua conta."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Cria token JWT
        try:
            access_token = create_access_token(user)
            logger.info(f"Login bem-sucedido para usuário: {email}")
            return Response({
                "access_token": access_token,
                "token_type": "bearer"
            })
        except Exception as e:
            logger.error(f"Erro ao criar token JWT: {e}")
            return Response(
                {"detail": "Erro ao gerar token de acesso. Tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """View para logout (stateless - apenas valida token)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        return Response({"message": "Logout realizado com sucesso"})


class MeView(APIView):
    """View que retorna informações do usuário logado"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserResponseSerializer(request.user)
        return Response(serializer.data)


class UpdateProfileView(APIView):
    """View para atualizar perfil do usuário logado"""
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Usuário não autenticado"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        new_email = request.data.get('email', '').strip()
        current_email = user.email
        
        # Verifica se o email mudou
        email_changed = new_email and new_email.lower() != current_email.lower()
        
        if email_changed:
            # Verifica se o novo email já está em uso
            if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
                return Response(
                    {"detail": "Este email já está em uso."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Remove email dos dados para não atualizar diretamente
            data_without_email = request.data.copy()
            data_without_email.pop('email', None)
            
            # Atualiza outros campos (nome, telefone, senha)
            serializer = UserUpdateSerializer(user, data=data_without_email, partial=True)
            if serializer.is_valid():
                serializer.save()
                
                # Invalida tokens anteriores não usados do usuário para mudança de email
                EmailChangeToken.objects.filter(
                    user=user,
                    used=False,
                    expires_at__gt=timezone.now()
                ).update(used=True)
                
                # Gera novo código de verificação de mudança de email
                code = generate_unique_verification_code(EmailChangeToken)
                expire_hours = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRE_HOURS', 24)
                expires_at = timezone.now() + timedelta(hours=expire_hours)
                
                # Cria registro do código
                email_change_token = EmailChangeToken.objects.create(
                    user=user,
                    new_email=new_email,
                    token=code,
                    used=False,
                    expires_at=expires_at
                )
                
                # Envia email de verificação para o novo email
                try:
                    email_service.send_email_change_email(
                        to_email=new_email,
                        verification_code=code,
                        user_name=user.name,
                        new_email=new_email
                    )
                except Exception as e:
                    logger.error(f"Erro ao enviar email de mudança: {e}")
                
                # Recarrega o usuário do banco
                user.refresh_from_db()
                return Response(
                    {
                        "message": "Perfil atualizado! Enviamos um email de verificação para o novo endereço. Verifique sua caixa de entrada para confirmar a mudança de email.",
                        "user": UserResponseSerializer(user).data
                    },
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Email não mudou, atualiza normalmente
            serializer = UserUpdateSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Recarrega o usuário do banco para garantir dados atualizados
                user.refresh_from_db()
                return Response(
                    UserResponseSerializer(user).data,
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Permite atualização parcial"""
        return self.put(request)


class ForgotPasswordView(APIView):
    """View para solicitar recuperação de senha"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Por segurança, sempre retorna sucesso mesmo se email não existir
            return Response({
                "message": "Se o email estiver cadastrado, você receberá um código de recuperação de senha."
            })
        
        # Invalida tokens anteriores não usados do usuário
        PasswordResetToken.objects.filter(
            user=user,
            used=False,
            expires_at__gt=timezone.now()
        ).update(used=True)
        
        # Gera novo código
        code = generate_unique_verification_code(PasswordResetToken)
        expire_hours = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRE_HOURS', 24)
        expires_at = timezone.now() + timedelta(hours=expire_hours)
        
        # Cria registro do código
        reset_token = PasswordResetToken.objects.create(
            user=user,
            token=code,
            used=False,
            expires_at=expires_at
        )
        
        # Envia email
        try:
            email_service.send_password_reset_email(
                to_email=user.email,
                reset_code=code,
                user_name=user.name
            )
        except Exception as e:
            logger.error(f"Erro ao enviar email de reset: {e}")
        
        return Response({
            "message": "Se o email estiver cadastrado, você receberá um código de recuperação de senha."
        })


class VerifyPasswordResetCodeView(APIView):
    """View para validar código de recuperação de senha"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']

        try:
            reset_token = PasswordResetToken.objects.get(
                token=code,
                used=False,
                expires_at__gt=timezone.now()
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"detail": "Código inválido ou expirado. Solicite um novo código de recuperação de senha."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "message": "Código válido.",
            "email": reset_token.user.email
        })


class ResetPasswordView(APIView):
    """View para redefinir senha usando código"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']
        
        # Busca código válido
        try:
            reset_token = PasswordResetToken.objects.get(
                token=code,
                used=False,
                expires_at__gt=timezone.now()
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"detail": "Código inválido ou expirado. Solicite um novo código de recuperação de senha."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Atualiza senha
        user = reset_token.user
        user.set_password(new_password)
        user.save()
        
        # Marca token como usado
        reset_token.used = True
        reset_token.save()
        
        access_token = create_access_token(user)

        return Response({
            "message": "Senha redefinida com sucesso! Você já está logado.",
            "access_token": access_token,
            "token_type": "bearer"
        })


class VerifyEmailView(APIView):
    """View para verificar email usando código"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        
        # Busca código válido
        try:
            verification_token = AccountVerificationToken.objects.get(
                token=code,
                used=False,
                expires_at__gt=timezone.now()
            )
        except AccountVerificationToken.DoesNotExist:
            # Tratamento idempotente: se já foi usado, considera verificado
            existing = AccountVerificationToken.objects.filter(token=code).order_by('-created_at').first()
            if existing:
                user = existing.user
                if not user.is_active:
                    user.is_active = True
                    user.save()
                access_token = create_access_token(user)
                return Response({
                    "message": "Email já verificado. Sua conta está ativa.",
                    "email": user.email,
                    "user_id": user.id,
                    "access_token": access_token,
                    "token_type": "bearer",
                })
            return Response(
                {"detail": "Código inválido ou expirado. Solicite um novo código de verificação."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ativa conta do usuário
        user = verification_token.user
        user.is_active = True
        user.save()
        
        verification_token.used = True
        verification_token.save()
        
        access_token = create_access_token(user)
        return Response({
            "message": "Email verificado com sucesso! Sua conta foi ativada.",
            "email": user.email,
            "user_id": user.id,
            "access_token": access_token,
            "token_type": "bearer",
        })


class ResendVerificationEmailView(APIView):
    """View para reenviar email de verificação"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResendVerificationEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email__iexact=email, is_active=False)
        except User.DoesNotExist:
            # Por segurança, sempre retorna sucesso mesmo se email não existir ou já estiver ativo
            return Response({
                "message": "Se o email estiver cadastrado e não verificado, você receberá um novo código de verificação."
            })
        
        # Invalida tokens anteriores não usados do usuário
        AccountVerificationToken.objects.filter(
            user=user,
            used=False,
            expires_at__gt=timezone.now()
        ).update(used=True)
        
        # Gera novo código de verificação
        code = generate_unique_verification_code(AccountVerificationToken)
        expire_hours = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRE_HOURS', 24)
        expires_at = timezone.now() + timedelta(hours=expire_hours)
        
        # Cria registro do código
        verification_token = AccountVerificationToken.objects.create(
            user=user,
            token=code,
            used=False,
            expires_at=expires_at
        )
        
        # Envia email de verificação
        try:
            email_service.send_verification_email(
                to_email=user.email,
                verification_code=code,
                user_name=user.name
            )
        except Exception as e:
            logger.error(f"Erro ao enviar email de verificação: {e}")
        
        return Response({
            "message": "Se o email estiver cadastrado e não verificado, você receberá um novo código de verificação."
        })


class ResendEmailChangeVerificationView(APIView):
    """View para reenviar email de verificação de mudança de email"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Busca o token de mudança de email mais recente não usado
        try:
            email_change_token = EmailChangeToken.objects.filter(
                user=user,
                used=False,
                expires_at__gt=timezone.now()
            ).order_by('-created_at').first()
            
            if not email_change_token:
                return Response(
                    {"detail": "Não há solicitação de mudança de email pendente."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Invalida tokens anteriores não usados do usuário
            EmailChangeToken.objects.filter(
                user=user,
                used=False,
                expires_at__gt=timezone.now()
            ).exclude(pk=email_change_token.pk).update(used=True)
            
            # Reenvia email de verificação de mudança
            try:
                email_service.send_email_change_email(
                    to_email=email_change_token.new_email,
                    verification_code=email_change_token.token,
                    user_name=user.name,
                    new_email=email_change_token.new_email
                )
            except Exception as e:
                logger.error(f"Erro ao enviar email de mudança: {e}")
            
            return Response({
                "message": "Email de verificação reenviado com sucesso."
            })
            
        except Exception as e:
            logger.error(f"Erro ao reenviar email de mudança: {e}")
            return Response(
                {"detail": "Erro ao reenviar email de verificação."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyEmailChangeView(APIView):
    """View para verificar mudança de email usando código"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        
        # Busca código válido
        try:
            email_change_token = EmailChangeToken.objects.get(
                token=code,
                used=False,
                expires_at__gt=timezone.now()
            )
        except EmailChangeToken.DoesNotExist:
            return Response(
                {"detail": "Código inválido ou expirado. Solicite uma nova mudança de email."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verifica se o novo email já está em uso por outro usuário
        if User.objects.filter(email__iexact=email_change_token.new_email).exclude(pk=email_change_token.user.pk).exists():
            # Marca token como usado mesmo que falhe
            email_change_token.used = True
            email_change_token.save()
            return Response(
                {"detail": "Este email já está em uso por outra conta."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Atualiza email do usuário
        user = email_change_token.user
        user.email = email_change_token.new_email
        user.save()
        
        # Marca token como usado
        email_change_token.used = True
        email_change_token.save()
        
        return Response({
            "message": "Email alterado com sucesso! Seu novo email foi confirmado e já está ativo."
        })
