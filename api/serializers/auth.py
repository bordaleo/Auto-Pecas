from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Serializer para login"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class TokenSerializer(serializers.Serializer):
    """Serializer para token JWT"""
    access_token = serializers.CharField()
    token_type = serializers.CharField(default='bearer')


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer para solicitar reset de senha"""
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer para reset de senha"""
    code = serializers.CharField(required=False, allow_blank=False)
    token = serializers.CharField(required=False, allow_blank=False)
    new_password = serializers.CharField(required=True, write_only=True)
    password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        code = attrs.get('code') or attrs.get('token')
        if not code:
            raise serializers.ValidationError({"code": "Código de recuperação é obrigatório"})
        attrs['code'] = str(code).strip()

        if attrs['new_password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"new_password": "As senhas não coincidem"})
        if len(attrs['new_password']) < 6:
            raise serializers.ValidationError({"new_password": "A senha deve ter no mínimo 6 caracteres"})
        return attrs


class MessageSerializer(serializers.Serializer):
    """Serializer para mensagens simples"""
    message = serializers.CharField()


class VerifyEmailSerializer(serializers.Serializer):
    """Serializer para verificação de email"""
    code = serializers.CharField(required=False, allow_blank=False)
    token = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        code = attrs.get('code') or attrs.get('token')
        if not code:
            raise serializers.ValidationError({"code": "Código de verificação é obrigatório"})

        code = str(code).strip()
        if not code.isdigit() or len(code) != 4:
            raise serializers.ValidationError({"code": "Informe o código de 4 dígitos enviado por email."})
        attrs['code'] = code
        return attrs


class ResendVerificationEmailSerializer(serializers.Serializer):
    """Serializer para reenviar email de verificação"""
    email = serializers.EmailField(required=True)