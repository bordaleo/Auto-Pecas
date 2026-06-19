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
    pix_key = models.CharField(
        max_length=120, blank=True, default='', verbose_name='Chave PIX para repasse',
    )
    balance_available = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Saldo disponível',
    )
    balance_pending = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Saldo pendente (saques)',
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


class PartCondition(models.TextChoices):
    NEW = 'new', 'Nova'
    USED = 'used', 'Usada'
    RECONDITIONED = 'reconditioned', 'Recondicionada'


class PartOrigin(models.TextChoices):
    ORIGINAL = 'original', 'Original (OEM)'
    PARALLEL = 'parallel', 'Paralela'
    REMANUFACTURED = 'remanufactured', 'Remanufaturada'


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
    cost_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Custo de aquisição",
        help_text="Usado para calcular margem nas peças da plataforma",
    )
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Preço anterior"
    )
    stock = models.PositiveIntegerField(default=0, verbose_name="Estoque")
    weight_kg = models.DecimalField(
        max_digits=6, decimal_places=3, default=Decimal('1.000'), verbose_name="Peso (kg)",
    )
    width_cm = models.PositiveIntegerField(default=20, verbose_name="Largura (cm)")
    height_cm = models.PositiveIntegerField(default=10, verbose_name="Altura (cm)")
    length_cm = models.PositiveIntegerField(default=30, verbose_name="Comprimento (cm)")
    part_condition = models.CharField(
        max_length=20, choices=PartCondition.choices, default=PartCondition.NEW,
        verbose_name='Condição',
    )
    part_origin = models.CharField(
        max_length=20, choices=PartOrigin.choices, default=PartOrigin.ORIGINAL,
        verbose_name='Origem',
    )
    warranty_days = models.PositiveIntegerField(
        default=90, verbose_name='Garantia (dias)',
    )
    view_count = models.PositiveIntegerField(default=0, verbose_name='Visualizações')
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


class OrderGroup(models.Model):
    """Agrupa sub-pedidos de um checkout (multi-vendedor)."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='order_groups', verbose_name='Usuário',
    )
    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_code = models.CharField(max_length=40, blank=True, default='')
    payment_preference_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    payment_id = models.CharField(max_length=255, blank=True, default='', db_index=True)
    payment_method = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'order_groups'
        ordering = ['-created_at']

    def __str__(self):
        return f'Grupo #{self.id}'


class Order(models.Model):
    """Pedido de compra de autopeças."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name="Usuário"
    )
    order_group = models.ForeignKey(
        OrderGroup,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Grupo de checkout',
    )
    fulfillment_seller = models.ForeignKey(
        'Seller',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fulfillment_orders',
        verbose_name='Loja responsável pelo envio',
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
    shipping_service_name = models.CharField(
        max_length=80, blank=True, default='', verbose_name="Serviço de frete",
    )
    shipping_days = models.PositiveIntegerField(null=True, blank=True, verbose_name="Prazo (dias)")
    shipping_provider = models.CharField(
        max_length=40, blank=True, default='fixed', verbose_name="Provedor de frete",
    )
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
    item_shipping_status = models.CharField(
        max_length=20,
        choices=ShippingStatus.choices,
        default=ShippingStatus.PENDING,
        verbose_name='Status envio (vendedor)',
    )
    item_tracking_code = models.CharField(max_length=80, blank=True, default='', verbose_name='Rastreio')
    item_carrier = models.CharField(max_length=80, blank=True, default='', verbose_name='Transportadora')
    item_shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='Enviado em')
    seller_balance_credited = models.BooleanField(default=False, verbose_name='Repasse creditado')

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
    origin_zip = models.CharField(
        max_length=12, blank=True, default='01310100', verbose_name='CEP de origem (frete)',
    )
    melhor_envio_token = models.CharField(
        max_length=255, blank=True, default='', verbose_name='Token Melhor Envio',
    )
    melhor_envio_sandbox = models.BooleanField(default=True, verbose_name='Melhor Envio sandbox')
    stock_reservation_minutes = models.PositiveIntegerField(
        default=30, verbose_name='Reserva de estoque (minutos)',
    )
    minimum_payout_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('50.00'),
        verbose_name='Saque mínimo vendedor',
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


class PayoutStatus(models.TextChoices):
    PENDING = 'pending', 'Aguardando'
    PROCESSING = 'processing', 'Em processamento'
    PAID = 'paid', 'Pago'
    REJECTED = 'rejected', 'Rejeitado'


class SellerPayout(models.Model):
    """Solicitação de saque do vendedor (repasse manual via PIX)."""
    seller = models.ForeignKey(
        Seller, on_delete=models.CASCADE, related_name='payouts', verbose_name='Vendedor',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Valor')
    pix_key = models.CharField(max_length=120, verbose_name='Chave PIX')
    status = models.CharField(
        max_length=20, choices=PayoutStatus.choices, default=PayoutStatus.PENDING, db_index=True,
    )
    admin_notes = models.TextField(blank=True, default='', verbose_name='Notas admin')
    payment_reference = models.CharField(
        max_length=120, blank=True, default='', verbose_name='Comprovante / ID PIX',
    )
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Processado em')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Repasse vendedor'
        verbose_name_plural = 'Repasses vendedores'
        db_table = 'seller_payouts'
        ordering = ['-created_at']

    def __str__(self):
        return f'Saque {self.seller.store_name} — R$ {self.amount}'


class StockReservation(models.Model):
    """Reserva temporária de estoque durante checkout pendente."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='stock_reservations', verbose_name='Peça',
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, null=True, blank=True,
        related_name='stock_reservations', verbose_name='Pedido',
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='stock_reservations', verbose_name='Usuário',
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name='Quantidade')
    expires_at = models.DateTimeField(verbose_name='Expira em')
    released = models.BooleanField(default=False, db_index=True, verbose_name='Liberada')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Reserva de estoque'
        verbose_name_plural = 'Reservas de estoque'
        db_table = 'stock_reservations'
        indexes = [models.Index(fields=['product', 'released', 'expires_at'])]

    def __str__(self):
        return f'Reserva {self.quantity}x {self.product.name}'


class VehicleBrand(models.Model):
    """Marca de veículo para filtro de compatibilidade."""
    name = models.CharField(max_length=80, unique=True, verbose_name='Marca')
    slug = models.SlugField(max_length=80, unique=True, db_index=True, verbose_name='Slug')
    is_active = models.BooleanField(default=True, verbose_name='Ativa')

    class Meta:
        verbose_name = 'Marca veículo'
        verbose_name_plural = 'Marcas veículos'
        db_table = 'vehicle_brands'
        ordering = ['name']

    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    """Modelo de veículo com faixa de anos."""
    brand = models.ForeignKey(
        VehicleBrand, on_delete=models.CASCADE, related_name='models', verbose_name='Marca',
    )
    name = models.CharField(max_length=120, verbose_name='Modelo')
    slug = models.SlugField(max_length=120, verbose_name='Slug')
    year_start = models.PositiveIntegerField(verbose_name='Ano inicial')
    year_end = models.PositiveIntegerField(verbose_name='Ano final')
    is_active = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        verbose_name = 'Modelo veículo'
        verbose_name_plural = 'Modelos veículos'
        db_table = 'vehicle_models'
        ordering = ['brand__name', 'name']
        unique_together = [['brand', 'slug']]

    def __str__(self):
        return f'{self.brand.name} {self.name} ({self.year_start}-{self.year_end})'


class ProductVehicleCompatibility(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='vehicle_compatibilities', verbose_name='Peça',
    )
    vehicle_model = models.ForeignKey(
        VehicleModel, on_delete=models.CASCADE, related_name='product_links', verbose_name='Veículo',
    )

    class Meta:
        verbose_name = 'Compatibilidade veicular'
        verbose_name_plural = 'Compatibilidades veiculares'
        db_table = 'product_vehicle_compatibilities'
        unique_together = [['product', 'vehicle_model']]

    def __str__(self):
        return f'{self.product.name} → {self.vehicle_model}'


class ProductReview(models.Model):
    """Avaliação de peça por comprador."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='reviews', verbose_name='Peça',
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='product_reviews', verbose_name='Usuário',
    )
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviews', verbose_name='Item do pedido',
    )
    rating = models.PositiveSmallIntegerField(verbose_name='Nota (1-5)')
    title = models.CharField(max_length=120, blank=True, default='', verbose_name='Título')
    comment = models.TextField(blank=True, default='', verbose_name='Comentário')
    is_verified_purchase = models.BooleanField(default=False, verbose_name='Compra verificada')
    is_visible = models.BooleanField(default=True, verbose_name='Visível')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'
        db_table = 'product_reviews'
        ordering = ['-created_at']
        unique_together = [['product', 'user', 'order_item']]

    def __str__(self):
        return f'{self.rating}★ — {self.product.name}'


class ReturnStatus(models.TextChoices):
    REQUESTED = 'requested', 'Solicitada'
    APPROVED = 'approved', 'Aprovada'
    REJECTED = 'rejected', 'Rejeitada'
    ITEM_SHIPPED = 'item_shipped', 'Item enviado pelo cliente'
    RECEIVED = 'received', 'Item recebido'
    REFUNDED = 'refunded', 'Reembolsado'
    CLOSED = 'closed', 'Encerrada'


class ReturnRequest(models.Model):
    """Solicitação de troca/devolução."""
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='return_requests', verbose_name='Pedido',
    )
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, related_name='return_requests', verbose_name='Item',
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='return_requests', verbose_name='Cliente',
    )
    seller = models.ForeignKey(
        Seller, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='return_requests', verbose_name='Vendedor',
    )
    reason = models.CharField(max_length=80, verbose_name='Motivo')
    description = models.TextField(blank=True, default='', verbose_name='Descrição')
    status = models.CharField(
        max_length=20, choices=ReturnStatus.choices, default=ReturnStatus.REQUESTED, db_index=True,
    )
    seller_response = models.TextField(blank=True, default='', verbose_name='Resposta vendedor')
    admin_notes = models.TextField(blank=True, default='', verbose_name='Notas admin')
    refund_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Valor reembolso',
    )
    return_tracking_code = models.CharField(
        max_length=80, blank=True, default='', verbose_name='Rastreio devolução',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Devolução'
        verbose_name_plural = 'Devoluções'
        db_table = 'return_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'Devolução #{self.id} — pedido #{self.order_id}'


class ProductConversation(models.Model):
    """Conversa comprador ↔ vendedor sobre uma peça."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='conversations', verbose_name='Peça',
    )
    buyer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='product_conversations', verbose_name='Comprador',
    )
    seller = models.ForeignKey(
        Seller, on_delete=models.CASCADE, related_name='conversations', verbose_name='Vendedor',
    )
    last_message_at = models.DateTimeField(auto_now_add=True, verbose_name='Última mensagem')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Conversa sobre peça'
        verbose_name_plural = 'Conversas sobre peças'
        db_table = 'product_conversations'
        unique_together = [['product', 'buyer']]
        ordering = ['-last_message_at']

    def __str__(self):
        return f'Chat {self.product.name} ({self.buyer.email})'


class ProductMessage(models.Model):
    conversation = models.ForeignKey(
        ProductConversation, on_delete=models.CASCADE, related_name='messages', verbose_name='Conversa',
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='product_messages', verbose_name='Remetente',
    )
    body = models.TextField(verbose_name='Mensagem')
    is_read = models.BooleanField(default=False, verbose_name='Lida')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Enviada em')

    class Meta:
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        db_table = 'product_messages'
        ordering = ['created_at']

    def __str__(self):
        return f'Msg #{self.id} — {self.sender.email}'


class NotificationType(models.TextChoices):
    ORDER_PAID = 'order_paid', 'Pagamento confirmado'
    ORDER_SHIPPED = 'order_shipped', 'Pedido enviado'
    ORDER_TRACKING = 'order_tracking', 'Rastreio atualizado'
    SELLER_NEW_ORDER = 'seller_new_order', 'Nova venda'
    CHAT_MESSAGE = 'chat_message', 'Nova mensagem'
    RETURN_OPENED = 'return_opened', 'Devolução aberta'
    RETURN_APPROVED = 'return_approved', 'Devolução aprovada'
    PAYOUT_PAID = 'payout_paid', 'Saque pago'
    INVOICE_ISSUED = 'invoice_issued', 'Nota fiscal emitida'


class UserNotification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications', verbose_name='Usuário',
    )
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices, db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default='')
    link = models.CharField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'user_notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} → {self.user.email}'


class InvoiceStatus(models.TextChoices):
    REQUESTED = 'requested', 'Solicitada'
    PROCESSING = 'processing', 'Em emissão'
    ISSUED = 'issued', 'Emitida'
    REJECTED = 'rejected', 'Rejeitada'


class InvoiceRequest(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='invoice_requests', verbose_name='Pedido',
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='invoice_requests', verbose_name='Cliente',
    )
    seller = models.ForeignKey(
        Seller, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoice_requests', verbose_name='Vendedor',
    )
    cnpj = models.CharField(max_length=20, verbose_name='CNPJ')
    company_name = models.CharField(max_length=255, verbose_name='Razão social')
    company_email = models.EmailField(blank=True, default='', verbose_name='E-mail fiscal')
    status = models.CharField(
        max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.REQUESTED, db_index=True,
    )
    invoice_number = models.CharField(max_length=80, blank=True, default='', verbose_name='Número NF-e')
    invoice_url = models.URLField(max_length=500, blank=True, default='', verbose_name='PDF/XML')
    admin_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoice_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f'NF-e pedido #{self.order_id} — {self.status}'


class ProductViewEvent(models.Model):
    """Registro de visualização para analytics."""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='view_events', verbose_name='Peça',
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_views',
    )
    session_key = models.CharField(max_length=64, blank=True, default='', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'product_view_events'
        indexes = [models.Index(fields=['product', '-created_at'])]

