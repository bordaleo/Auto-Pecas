from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator
from api.models import User
import re


class UserSerializer(serializers.ModelSerializer):
    """Serializer para o modelo User"""
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'is_active', 'is_staff', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserRegisterSerializer(serializers.ModelSerializer):
    """Serializer para registro de usuário"""
    email = serializers.EmailField(required=True, validators=[])
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'password_confirm']
    
    def validate_email(self, value):
        """Valida formato de email mais rigoroso"""
        if not value:
            raise serializers.ValidationError("O email é obrigatório")
        
        # Validação básica de formato
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$'
        if not re.match(email_regex, value):
            raise serializers.ValidationError("Por favor, insira um email válido (exemplo: seu@email.com)")
        
        # Validação adicional: verifica se tem domínio válido
        parts = value.split('@')
        if len(parts) != 2:
            raise serializers.ValidationError("Email inválido")
        
        domain = parts[1]
        if '.' not in domain or domain.startswith('.') or domain.endswith('.'):
            raise serializers.ValidationError("Email inválido")
        
        domain_parts = domain.split('.')
        if len(domain_parts) < 2 or any(not part or len(part) < 2 for part in domain_parts):
            raise serializers.ValidationError("Email inválido")
        
        normalized_email = value.lower().strip()

        # Permite "re-cadastro" apenas para contas pendentes de verificação.
        # Se já existir conta ativa, mantém bloqueio.
        existing_user = User.objects.filter(email__iexact=normalized_email).first()
        if existing_user:
            if existing_user.is_active:
                raise serializers.ValidationError(
                    "Este email já está cadastrado. Use Entrar ou cadastre outro email."
                )
            self.context['existing_inactive_user'] = existing_user

        return normalized_email
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "As senhas não coincidem"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        existing_inactive_user = self.context.get('existing_inactive_user')

        # Usuário ativo imediatamente em desenvolvimento (evita bloqueio por verificação de email)
        from django.conf import settings as django_settings
        is_active = not django_settings.DEBUG

        if existing_inactive_user:
            existing_inactive_user.name = validated_data['name']
            existing_inactive_user.is_active = is_active
            existing_inactive_user.set_password(password)
            existing_inactive_user.save()
            self.context['reused_inactive_user'] = True
            return existing_inactive_user

        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=password,
            is_active=is_active,
        )
        self.context['reused_inactive_user'] = False
        return user


class UserResponseSerializer(serializers.ModelSerializer):
    """Serializer de resposta para o usuário"""
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'is_active', 'is_staff', 'is_superuser', 'created_at', 'updated_at']
        read_only_fields = ['id', 'is_active', 'is_staff', 'is_superuser', 'created_at', 'updated_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer para atualização de perfil do usuário"""
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password_confirm = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'phone', 'password', 'password_confirm']
    
    def validate_email(self, value):
        """Valida se o email não está em uso por outro usuário e formato válido"""
        if not value:
            raise serializers.ValidationError("O email é obrigatório")
        
        # Validação básica de formato
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]{2,}$'
        if not re.match(email_regex, value):
            raise serializers.ValidationError("Por favor, insira um email válido (exemplo: seu@email.com)")
        
        # Validação adicional: verifica se tem domínio válido
        parts = value.split('@')
        if len(parts) != 2:
            raise serializers.ValidationError("Email inválido")
        
        domain = parts[1]
        if '.' not in domain or domain.startswith('.') or domain.endswith('.'):
            raise serializers.ValidationError("Email inválido")
        
        domain_parts = domain.split('.')
        if len(domain_parts) < 2 or any(not part or len(part) < 2 for part in domain_parts):
            raise serializers.ValidationError("Email inválido")
        
        # Verifica se o email não está em uso por outro usuário
        user = self.instance
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("Este email já está em uso.")
        
        return value.lower().strip()
    
    def validate(self, attrs):
        """Valida se as senhas coincidem quando fornecidas"""
        # Remove campos vazios ou None
        if 'password' in attrs:
            password = str(attrs.get('password', '')).strip()
            if not password:
                attrs.pop('password', None)
        else:
            password = None
            
        if 'password_confirm' in attrs:
            password_confirm = str(attrs.get('password_confirm', '')).strip()
            if not password_confirm:
                attrs.pop('password_confirm', None)
        else:
            password_confirm = None
        
        # Se algum campo de senha foi fornecido, valida
        if password or password_confirm:
            if not password:
                raise serializers.ValidationError({"password": "A senha é obrigatória quando você confirma a senha."})
            if not password_confirm:
                raise serializers.ValidationError({"password_confirm": "A confirmação de senha é obrigatória."})
            if password != password_confirm:
                raise serializers.ValidationError({"password": "As senhas não coincidem."})
            # Valida a senha apenas se fornecida
            validate_password(password)
        
        return attrs
    
    def update(self, instance, validated_data):
        """Atualiza o usuário"""
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirm', None)
        
        # Atualiza campos normais (permite None para phone)
        for attr, value in validated_data.items():
            if value is not None or attr == 'phone':  # phone pode ser None
                setattr(instance, attr, value if value != '' else None)
        
        # Atualiza senha se fornecida
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance
