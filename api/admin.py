from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    User, Seller, Order, OrderItem, OrderStatus, Category, Product, ProductImage,
    PasswordResetToken, SystemConfig, OpsAlertEvent, SiteEngagementTotals,
    Coupon, AbandonedCart,
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_sku', 'unit_price', 'quantity', 'image_url', 'seller', 'platform_fee', 'seller_earning']


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'user', 'status', 'commission_rate', 'created_at']
    list_filter = ['status']
    search_fields = ['store_name', 'user__email', 'document']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['id', 'email', 'name', 'is_active', 'is_staff', 'is_superuser', 'created_at', 'orders_count']
    list_filter = ['is_active', 'is_staff', 'is_superuser', 'created_at']
    search_fields = ['email', 'name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'last_login']

    fieldsets = (
        ('Informações Básicas', {'fields': ('email', 'name', 'phone')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Datas', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'name', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_active')}),
    )

    def orders_count(self, obj):
        count = obj.orders.count()
        if count > 0:
            url = reverse('admin:api_order_changelist') + f'?user__id__exact={obj.id}'
            return format_html('<a href="{}">{} pedido(s)</a>', url, count)
        return '0 pedidos'
    orders_count.short_description = 'Pedidos'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'sort_order', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'slug']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'brand', 'price', 'stock', 'is_active', 'is_featured', 'category', 'created_at']
    list_filter = ['is_active', 'is_featured', 'category', 'brand']
    search_fields = ['name', 'sku', 'oem_code', 'brand']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user_link', 'status_display', 'amount', 'payment_method', 'customer_name', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['id', 'user__email', 'customer_name', 'payment_id']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [OrderItemInline]
    actions = ['mark_as_approved', 'mark_as_rejected', 'mark_as_pending']

    def user_link(self, obj):
        url = reverse('admin:api_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'Usuário'

    def status_display(self, obj):
        colors = {'pending': '#f59e0b', 'approved': '#10b981', 'rejected': '#ef4444'}
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            colors.get(obj.status, '#6b7280'),
            obj.get_status_display(),
        )
    status_display.short_description = 'Status'

    def mark_as_approved(self, request, queryset):
        from api.views.shop_views import approve_shop_order
        for order in queryset:
            approve_shop_order(order)
        self.message_user(request, f'{queryset.count()} pedido(s) aprovado(s).')
    mark_as_approved.short_description = 'Marcar como aprovado'

    def mark_as_rejected(self, request, queryset):
        queryset.update(status=OrderStatus.REJECTED)
        self.message_user(request, f'{queryset.count()} pedido(s) rejeitado(s).')
    mark_as_rejected.short_description = 'Marcar como rejeitado'

    def mark_as_pending(self, request, queryset):
        queryset.update(status=OrderStatus.PENDING)
        self.message_user(request, f'{queryset.count()} pedido(s) pendente(s).')
    mark_as_pending.short_description = 'Marcar como pendente'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'token', 'used', 'expires_at', 'created_at']
    list_filter = ['used', 'expires_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['created_at']


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'maintenance_mode', 'free_shipping_min', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(OpsAlertEvent)
class OpsAlertEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'category', 'message']
    readonly_fields = ['created_at', 'category', 'message', 'detail', 'body_excerpt', 'extra']
    ordering = ['-created_at']


@admin.register(SiteEngagementTotals)
class SiteEngagementTotalsAdmin(admin.ModelAdmin):
    list_display = ['id', 'instagram_clicks', 'tiktok_clicks', 'support_modal_opens', 'updated_at']
    readonly_fields = ['id', 'instagram_clicks', 'tiktok_clicks', 'support_modal_opens', 'updated_at']

    def has_add_permission(self, request):
        return False


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'first_purchase_only', 'used_count', 'is_active']
    search_fields = ['code']
    list_filter = ['is_active', 'first_purchase_only']


@admin.register(AbandonedCart)
class AbandonedCartAdmin(admin.ModelAdmin):
    list_display = ['email', 'subtotal', 'reminder_sent_at', 'recovered_at', 'updated_at']
    search_fields = ['email']
    readonly_fields = ['created_at', 'updated_at']


admin.site.site_header = "Galelugi Peças — Administração"
admin.site.site_title = "Galelugi Admin"
admin.site.index_title = "Painel de Controle"
