from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinLengthValidator
from decimal import Decimal


class UserManager(BaseUserManager):
    """Manager customizado para o modelo User"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Cria e salva um usuário normal"""
        if not email:
            raise ValueError('O email é obrigatório')   
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Cria e salva um superusuário"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser deve ter is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser deve ter is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Modelo de usuário personalizado"""
    email = models.EmailField(unique=True, db_index=True, verbose_name="Email")
    name = models.CharField(max_length=255, verbose_name="Nome")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone")
    shipping_zip = models.CharField(max_length=12, blank=True, default='', verbose_name="CEP")
    shipping_address = models.CharField(max_length=255, blank=True, default='', verbose_name="Endereço")
    shipping_city = models.CharField(max_length=120, blank=True, default='', verbose_name="Cidade")
    shipping_state = models.CharField(max_length=2, blank=True, default='', verbose_name="UF")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    is_staff = models.BooleanField(default=False, verbose_name="Staff")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.email})"


class Seller(models.Model):
    """Loja de vendedor no marketplace Galelugi."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Aguardando aprovação'
        ACTIVE = 'active', 'Ativa'
        SUSPENDED = 'suspended', 'Suspensa'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='seller_profile',
        verbose_name='Usuário',
    )
    store_name = models.CharField(max_length=120, verbose_name='Nome da loja')
    slug = models.SlugField(max_length=120, unique=True, db_index=True, verbose_name='Slug')
    description = models.TextField(blank=True, default='', verbose_name='Descrição')
    document = models.CharField(max_length=20, blank=True, default='', verbose_name='CPF/CNPJ')
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='Telefone')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name='Status',
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Comissão personalizada (%)',
        help_text='Vazio = usa taxa padrão da plataforma',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'
        db_table = 'sellers'
        ordering = ['-created_at']

    def __str__(self):
        return self.store_name


class DeliveryMethod(models.TextChoices):
    DELIVERY = 'delivery', 'Entrega'
    PICKUP = 'pickup', 'Retirada na loja'


class OrderStatus(models.TextChoices):
    PENDING = 'pending', 'Pendente'
    APPROVED = 'approved', 'Aprovado'
    REJECTED = 'rejected', 'Rejeitado'


class ShippingStatus(models.TextChoices):
    PENDING = 'pending', 'Aguardando envio'
    PROCESSING = 'processing', 'Em separação'
    SHIPPED = 'shipped', 'Enviado'
    DELIVERED = 'delivered', 'Entregue'


class CouponDiscountType(models.TextChoices):
    PERCENT = 'percent', 'Percentual'
    FIXED = 'fixed', 'Valor fixo'


class Category(models.Model):
    """Categoria de autopeças (ex: Motor, Freios, Suspensão)."""
    name = models.CharField(max_length=120, verbose_name="Nome")
    slug = models.SlugField(max_length=120, unique=True, db_index=True, verbose_name="Slug")
    icon = models.CharField(max_length=40, blank=True, default='', verbose_name="Ícone (emoji ou classe)")
    description = models.TextField(blank=True, default='', verbose_name="Descrição")
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        db_table = 'categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Peça automotiva disponível para venda."""
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name="Categoria",
    )
    name = models.CharField(max_length=255, verbose_name="Nome")
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name="Slug")
    description = models.TextField(blank=True, default='', verbose_name="Descrição")
    sku = models.CharField(max_length=80, blank=True, default='', db_index=True, verbose_name="SKU / Código")
    oem_code = models.CharField(max_length=80, blank=True, default='', db_index=True, verbose_name="Código OEM")
    brand = models.CharField(max_length=120, blank=True, default='', db_index=True, verbose_name="Marca")
    compatible_vehicles = models.TextField(
        blank=True,
        default='',
        verbose_name="Veículos compatíveis",
        help_text="Ex: Gol 1.0 2012-2016; Palio 1.4 2010-2015",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Preço anterior"
    )
    stock = models.PositiveIntegerField(default=0, verbose_name="Estoque")
    image_url = models.URLField(max_length=500, blank=True, default='', verbose_name="Imagem principal")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    is_featured = models.BooleanField(default=False, verbose_name="Destaque")
    seller = models.ForeignKey(
        'Seller',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Vendedor',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products_created',
        verbose_name="Cadastrado por",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Peça"
        verbose_name_plural = "Peças"
        db_table = 'products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['is_featured', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku or self.slug})"

    @property
    def in_stock(self):
        return self.stock > 0


class ProductImage(models.Model):
    """Imagens adicionais de uma peça."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="Peça",
    )
    url = models.URLField(max_length=500, verbose_name="URL")
    alt_text = models.CharField(max_length=255, blank=True, default='', verbose_name="Texto alternativo")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Imagem da peça"
        verbose_name_plural = "Imagens das peças"
        db_table = 'product_images'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"Imagem #{self.id} — {self.product.name}"


class Order(models.Model):
    """Pedido de compra de autopeças."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="Usuário"
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name="Status"
    )
    payment_method = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Método de Pagamento"
    )
    payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="ID do Pagamento"
    )
    payment_preference_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="ID da Preferência"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor"
    )
    order_email = models.EmailField(
        null=True,
        blank=True,
        verbose_name="Email para Envio do Pedido"
    )
    customer_name = models.CharField(max_length=255, blank=True, default='', verbose_name="Nome do cliente")
    customer_phone = models.CharField(max_length=20, blank=True, default='', verbose_name="Telefone")
    shipping_address = models.CharField(max_length=255, blank=True, default='', verbose_name="Endereço")
    shipping_city = models.CharField(max_length=120, blank=True, default='', verbose_name="Cidade")
    shipping_state = models.CharField(max_length=2, blank=True, default='', verbose_name="UF")
    shipping_zip = models.CharField(max_length=12, blank=True, default='', verbose_name="CEP")
    delivery_method = models.CharField(
        max_length=20,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.DELIVERY,
        verbose_name="Forma de recebimento",
    )
    shipping_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Valor do frete",
    )
    notes = models.TextField(blank=True, default='', verbose_name="Observações")
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Desconto aplicado",
    )
    coupon_code = models.CharField(max_length=40, blank=True, default='', verbose_name="Cupom")
    tracking_code = models.CharField(max_length=80, blank=True, default='', verbose_name="Código de rastreio")
    carrier = models.CharField(max_length=80, blank=True, default='', verbose_name="Transportadora")
    shipping_status = models.CharField(
        max_length=20,
        choices=ShippingStatus.choices,
        default=ShippingStatus.PENDING,
        verbose_name="Status do envio",
    )
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name="Enviado em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Pedido #{self.id} - {self.user.name} ({self.get_status_display()})"


class OrderItem(models.Model):
    """Item de um pedido de autopeças."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Pedido",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name="Peça",
    )
    product_name = models.CharField(max_length=255, verbose_name="Nome da peça")
    product_sku = models.CharField(max_length=80, blank=True, default='', verbose_name="SKU")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço unitário")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Quantidade")
    image_url = models.URLField(max_length=500, blank=True, default='', verbose_name="Imagem")
    seller = models.ForeignKey(
        'Seller',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='Vendedor',
    )
    platform_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Comissão Galelugi',
    )
    seller_earning = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Repasse ao vendedor',
    )

    class Meta:
        verbose_name = "Item do pedido"
        verbose_name_plural = "Itens do pedido"
        db_table = 'order_items'

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class PasswordResetToken(models.Model):
    """Modelo de token para reset de senha"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name="Usuário"
    )
    token = models.CharField(max_length=255, unique=True, db_index=True, verbose_name="Token")
    used = models.BooleanField(default=False, verbose_name="Usado")
    expires_at = models.DateTimeField(verbose_name="Expira em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Token de Reset de Senha"
        verbose_name_plural = "Tokens de Reset de Senha"
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token para {self.user.email} - {'Usado' if self.used else 'Ativo'}"
    
    def is_valid(self):
        """Verifica se o token ainda é válido"""
        from django.utils import timezone
        return not self.used and self.expires_at > timezone.now()


class AccountVerificationToken(models.Model):
    """Modelo de token para verificação de conta por email"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='account_verification_tokens',
        verbose_name="Usuário"
    )
    token = models.CharField(max_length=255, unique=True, db_index=True, verbose_name="Token")
    used = models.BooleanField(default=False, verbose_name="Usado")
    expires_at = models.DateTimeField(verbose_name="Expira em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Token de Verificação de Conta"
        verbose_name_plural = "Tokens de Verificação de Conta"
        db_table = 'account_verification_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token de verificação para {self.user.email} - {'Usado' if self.used else 'Ativo'}"
    
    def is_valid(self):
        """Verifica se o token ainda é válido"""
        from django.utils import timezone
        return not self.used and self.expires_at > timezone.now()


class EmailChangeToken(models.Model):
    """Modelo de token para mudança de email"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_change_tokens',
        verbose_name="Usuário"
    )
    new_email = models.EmailField(verbose_name="Novo Email")
    token = models.CharField(max_length=255, unique=True, db_index=True, verbose_name="Token")
    used = models.BooleanField(default=False, verbose_name="Usado")
    expires_at = models.DateTimeField(verbose_name="Expira em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Token de Mudança de Email"
        verbose_name_plural = "Tokens de Mudança de Email"
        db_table = 'email_change_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token de mudança de email para {self.user.email} -> {self.new_email} - {'Usado' if self.used else 'Ativo'}"
    
    def is_valid(self):
        """Verifica se o token ainda é válido"""
        from django.utils import timezone
        return not self.used and self.expires_at > timezone.now()


class OrderEmailVerificationToken(models.Model):
    """Modelo de token para verificação de email de pedido"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='order_email_verification_tokens',
        verbose_name="Usuário"
    )
    email = models.EmailField(verbose_name="Email para Verificação")
    token = models.CharField(max_length=255, unique=True, db_index=True, verbose_name="Token")
    used = models.BooleanField(default=False, verbose_name="Usado")
    expires_at = models.DateTimeField(verbose_name="Expira em")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Token de Verificação de Email de Pedido"
        verbose_name_plural = "Tokens de Verificação de Email de Pedido"
        db_table = 'order_email_verification_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token de verificação de email de pedido para {self.user.email} -> {self.email} - {'Usado' if self.used else 'Ativo'}"
    
    def is_valid(self):
        """Verifica se o token ainda é válido"""
        from django.utils import timezone
        return not self.used and self.expires_at > timezone.now()


class SystemConfig(models.Model):
    """Configurações globais da loja Galelugi Peças."""

    store_name = models.CharField(max_length=120, default='Galelugi Peças', verbose_name="Nome da loja")
    store_tagline = models.CharField(
        max_length=255,
        default='Peças automotivas com qualidade e confiança',
        verbose_name="Slogan",
    )
    store_phone = models.CharField(max_length=20, blank=True, default='', verbose_name="Telefone")
    store_whatsapp = models.CharField(max_length=20, blank=True, default='', verbose_name="WhatsApp")
    store_email = models.EmailField(blank=True, default='', verbose_name="E-mail de contato")
    store_address = models.CharField(
        max_length=255,
        blank=True,
        default='Rua São Sabino, 262',
        verbose_name="Endereço",
    )
    free_shipping_min = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('299.00'), verbose_name="Frete grátis acima de"
    )
    marketplace_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('12.00'),
        verbose_name='Comissão do marketplace (%)',
        help_text='Percentual retido pela Galelugi em cada venda de vendedor',
    )
    maintenance_mode = models.BooleanField(default=False, verbose_name="Modo Manutenção")
    maintenance_message = models.TextField(null=True, blank=True, verbose_name="Mensagem de Manutenção")
    google_analytics_id = models.CharField(
        max_length=40, blank=True, default='', verbose_name="Google Analytics ID",
    )
    meta_pixel_id = models.CharField(
        max_length=40, blank=True, default='', verbose_name="Meta Pixel ID",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"
        db_table = 'system_config'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    def __str__(self):
        return self.store_name


class Coupon(models.Model):
    """Cupom de desconto."""
    code = models.CharField(max_length=40, unique=True, db_index=True, verbose_name="Código")
    discount_type = models.CharField(
        max_length=10, choices=CouponDiscountType.choices, default=CouponDiscountType.PERCENT,
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor do desconto")
    first_purchase_only = models.BooleanField(default=False, verbose_name="Somente primeira compra")
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Pedido mínimo",
    )
    usage_limit = models.PositiveIntegerField(null=True, blank=True, verbose_name="Limite de usos")
    used_count = models.PositiveIntegerField(default=0, verbose_name="Vezes usado")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Expira em")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cupom"
        verbose_name_plural = "Cupons"
        db_table = 'coupons'

    def __str__(self):
        return self.code


class AbandonedCart(models.Model):
    """Snapshot de carrinho para recuperação por e-mail."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='abandoned_carts',
    )
    email = models.EmailField(db_index=True, verbose_name="E-mail")
    items = models.JSONField(default=list, verbose_name="Itens")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    reminder_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Lembrete enviado em")
    recovered_at = models.DateTimeField(null=True, blank=True, verbose_name="Recuperado em")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Carrinho abandonado"
        verbose_name_plural = "Carrinhos abandonados"
        db_table = 'abandoned_carts'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Carrinho {self.email} — R$ {self.subtotal}"


class OpsAlertEvent(models.Model):
    """Cópia local de alertas enviados ao Discord/e-mail (ops_alerts)."""

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Quando", db_index=True)
    category = models.CharField(max_length=200, db_index=True, verbose_name="Categoria")
    message = models.TextField(verbose_name="Mensagem")
    detail = models.TextField(blank=True, default='', verbose_name="Detalhe")
    body_excerpt = models.TextField(blank=True, default='', verbose_name="Corpo (trecho)")
    extra = models.JSONField(null=True, blank=True, verbose_name="Extra")

    class Meta:
        verbose_name = "Evento de alerta (ops)"
        verbose_name_plural = "Eventos de alerta (ops)"
        db_table = "ops_alert_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.category} @ {self.created_at}"


class SiteEngagementTotals(models.Model):
    """Totais globais (landing): cliques em redes / aberturas de suporte. Singleton pk=1."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    instagram_clicks = models.PositiveBigIntegerField(default=0, verbose_name="Cliques Instagram")
    tiktok_clicks = models.PositiveBigIntegerField(default=0, verbose_name="Cliques TikTok")
    support_modal_opens = models.PositiveBigIntegerField(default=0, verbose_name="Aberturas modal suporte")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Totais de engajamento (site)"
        verbose_name_plural = "Totais de engajamento (site)"
        db_table = "site_engagement_totals"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_row(cls):
        row, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "instagram_clicks": 0,
                "tiktok_clicks": 0,
                "support_modal_opens": 0,
            },
        )
        return row

