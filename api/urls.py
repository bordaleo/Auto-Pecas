from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.auth_views import (
    RegisterView,
    LoginView,
    LogoutView,
    MeView,
    UpdateProfileView,
    ForgotPasswordView,
    VerifyPasswordResetCodeView,
    ResetPasswordView,
    VerifyEmailView,
    VerifyEmailChangeView,
    ResendVerificationEmailView,
    ResendEmailChangeVerificationView,
)
from .views.melhor_envio_views import MelhorEnvioOAuthCallbackView, MelhorEnvioOAuthInfoView
from .views.payment_views import (
    PaymentWebhookView,
    PaymentStatusView,
    PaymentProcessView,
)
from .views.product_views import (
    CategoryListView,
    ProductListView,
    ProductDetailView,
    ProductManageListCreateView,
    ProductManageDetailView,
    ProductImageUploadView,
    ProductBrandsView,
)
from .views.shop_views import (
    CheckoutView,
    ShopPaymentPreferenceView,
    ShopOrderListView,
    ShopOrderDetailView,
    ShippingQuoteView,
    CouponValidateView,
    CartSyncView,
)
from .views.seller_views import (
    SellerApplyView,
    SellerMeView,
    SellerCommissionPreviewView,
    SellerProductListCreateView,
    SellerProductDetailView,
    SellerImageUploadView,
    SellerPublicView,
)
from .views.contact_views import WhatsAppContactView
from .views.admin_views import (
    painel_dashboard_api,
    painel_ops_events_api,
    system_config_api,
    system_config_public_api,
    painel_session_api,
    painel_login_api,
    painel_logout_api,
    painel_order_detail_api,
    painel_sellers_api,
    painel_payouts_api,
    painel_finance_api,
    painel_invoices_api,
)
from .views.marketplace_views import (
    SellerPayoutSummaryView,
    SellerPayoutRequestView,
    SellerOrderListView,
    SellerOrderDetailView,
    ProductReviewListView,
    ProductReviewCreateView,
    VehicleBrandListView,
    VehicleModelListView,
    ReturnRequestListCreateView,
    ReturnRequestDetailView,
    SellerReturnListView,
    ChatConversationListView,
    ChatStartView,
    ChatMessagesView,
    ProductWhatsAppLinkView,
)
from .views.growth_views import (
    NotificationListView,
    NotificationUnreadCountView,
    VehicleLookupView,
    InvoiceRequestListCreateView,
    InvoiceRequestManageView,
    InvoiceNuvemFiscalStatusView,
    InvoiceEmitView,
    InvoiceNfePdfView,
    SellerAnalyticsView,
    SellerCsvImportView,
    SellerCsvTemplateView,
)
from .views.part_request_views import (
    PartRequestListCreateView,
    PartRequestDetailView,
    PartRequestSuggestionsView,
    SellerPartRequestListView,
    SellerPartRequestStatsView,
    PartRequestRespondView,
    PartRequestRateView,
    PartRequestConversationListView,
    PartRequestChatMessagesView,
)

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),

    # Autenticação
    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('auth/me', MeView.as_view(), name='me'),
    path('auth/profile', UpdateProfileView.as_view(), name='update-profile'),
    path('auth/verify-email', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/resend-verification-email', ResendVerificationEmailView.as_view(), name='resend-verification-email'),
    path('auth/resend-email-change-verification', ResendEmailChangeVerificationView.as_view(), name='resend-email-change-verification'),
    path('auth/verify-email-change', VerifyEmailChangeView.as_view(), name='verify-email-change'),
    path('auth/forgot-password', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/verify-reset-code', VerifyPasswordResetCodeView.as_view(), name='verify-reset-code'),
    path('auth/reset-password', ResetPasswordView.as_view(), name='reset-password'),

    # Catálogo (público)
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('products/', ProductListView.as_view(), name='products'),
    path('products/brands/', ProductBrandsView.as_view(), name='product-brands'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),

    # Gerenciamento de peças (staff)
    path('manage/products/', ProductManageListCreateView.as_view(), name='manage-products'),
    path('manage/products/<int:pk>/', ProductManageDetailView.as_view(), name='manage-product-detail'),
    path('manage/upload-image/', ProductImageUploadView.as_view(), name='manage-upload-image'),

    # Carrinho / pedidos
    path('shop/shipping/quote/', ShippingQuoteView.as_view(), name='shop-shipping-quote'),
    path('integrations/melhor-envio/callback/', MelhorEnvioOAuthCallbackView.as_view(), name='melhor-envio-callback'),
    path('integrations/melhor-envio/info/', MelhorEnvioOAuthInfoView.as_view(), name='melhor-envio-oauth-info'),
    path('shop/coupon/validate/', CouponValidateView.as_view(), name='shop-coupon-validate'),
    path('shop/cart/sync/', CartSyncView.as_view(), name='shop-cart-sync'),
    path('shop/checkout/', CheckoutView.as_view(), name='shop-checkout'),
    path('shop/orders/', ShopOrderListView.as_view(), name='shop-orders'),
    path('shop/orders/<int:order_id>/', ShopOrderDetailView.as_view(), name='shop-order-detail'),
    path('shop/payment/preference/', ShopPaymentPreferenceView.as_view(), name='shop-payment-preference'),

    # Pagamentos Mercado Pago
    path('payments/process', PaymentProcessView.as_view(), name='payment-process'),
    path('payments/webhook', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('payments/status/<str:preference_id>', PaymentStatusView.as_view(), name='payment-status'),

    # Marketplace — vendedores
    path('seller/apply/', SellerApplyView.as_view(), name='seller-apply'),
    path('seller/me/', SellerMeView.as_view(), name='seller-me'),
    path('seller/commission-preview/', SellerCommissionPreviewView.as_view(), name='seller-commission-preview'),
    path('seller/products/', SellerProductListCreateView.as_view(), name='seller-products'),
    path('seller/products/<int:pk>/', SellerProductDetailView.as_view(), name='seller-product-detail'),
    path('seller/upload-image/', SellerImageUploadView.as_view(), name='seller-upload-image'),
    path('seller/store/<slug:slug>/', SellerPublicView.as_view(), name='seller-public'),
    path('seller/payouts/', SellerPayoutSummaryView.as_view(), name='seller-payouts'),
    path('seller/payouts/request/', SellerPayoutRequestView.as_view(), name='seller-payout-request'),
    path('seller/orders/', SellerOrderListView.as_view(), name='seller-orders'),
    path('seller/orders/<int:item_id>/', SellerOrderDetailView.as_view(), name='seller-order-detail'),
    path('seller/returns/', SellerReturnListView.as_view(), name='seller-returns'),

    # Avaliações, veículos, devoluções, chat
    path('reviews/', ProductReviewCreateView.as_view(), name='review-create'),
    path('products/<int:product_id>/reviews/', ProductReviewListView.as_view(), name='product-reviews'),
    path('vehicles/brands/', VehicleBrandListView.as_view(), name='vehicle-brands'),
    path('vehicles/models/', VehicleModelListView.as_view(), name='vehicle-models'),
    path('vehicles/lookup/', VehicleLookupView.as_view(), name='vehicle-lookup'),

    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/unread/', NotificationUnreadCountView.as_view(), name='notifications-unread'),
    path('invoices/', InvoiceRequestListCreateView.as_view(), name='invoices'),
    path('invoices/nuvem-fiscal/status', InvoiceNuvemFiscalStatusView.as_view(), name='invoices-nuvem-status'),
    path('invoices/<int:pk>/emit/', InvoiceEmitView.as_view(), name='invoice-emit'),
    path('invoices/<int:pk>/nfe-pdf/', InvoiceNfePdfView.as_view(), name='invoice-nfe-pdf'),
    path('invoices/<int:pk>/', InvoiceRequestManageView.as_view(), name='invoice-manage'),
    path('seller/analytics/', SellerAnalyticsView.as_view(), name='seller-analytics'),
    path('seller/products/import/', SellerCsvImportView.as_view(), name='seller-csv-import'),
    path('seller/products/import/template/', SellerCsvTemplateView.as_view(), name='seller-csv-template'),

    path('returns/', ReturnRequestListCreateView.as_view(), name='returns'),
    path('returns/<int:pk>/', ReturnRequestDetailView.as_view(), name='return-detail'),
    path('chat/conversations/', ChatConversationListView.as_view(), name='chat-conversations'),
    path('chat/start/', ChatStartView.as_view(), name='chat-start'),
    path('chat/<int:conv_id>/messages/', ChatMessagesView.as_view(), name='chat-messages'),
    path('products/<int:product_id>/whatsapp/', ProductWhatsAppLinkView.as_view(), name='product-whatsapp'),

    # Pedidos de peça (demanda pública)
    path('part-requests/suggestions/', PartRequestSuggestionsView.as_view(), name='part-request-suggestions'),
    path('part-requests/', PartRequestListCreateView.as_view(), name='part-requests'),
    path('part-requests/conversations/', PartRequestConversationListView.as_view(), name='part-request-conversations'),
    path('part-requests/chat/<int:conv_id>/messages/', PartRequestChatMessagesView.as_view(), name='part-request-chat-messages'),
    path('part-requests/chat/<int:conv_id>/rate/', PartRequestRateView.as_view(), name='part-request-rate'),
    path('part-requests/<int:pk>/', PartRequestDetailView.as_view(), name='part-request-detail'),
    path('part-requests/<int:pk>/respond/', PartRequestRespondView.as_view(), name='part-request-respond'),
    path('seller/part-requests/stats/', SellerPartRequestStatsView.as_view(), name='seller-part-request-stats'),
    path('seller/part-requests/', SellerPartRequestListView.as_view(), name='seller-part-requests'),

    # Contato
    path('contact/whatsapp/', WhatsAppContactView.as_view(), name='contact-whatsapp'),

    # Config
    path('system-config', system_config_public_api, name='system-config-public'),
    path('admin/system-config', system_config_api, name='system-config-api'),
    path('painel/dashboard', painel_dashboard_api, name='painel-dashboard-api'),
    path('painel/ops-events', painel_ops_events_api, name='painel-ops-events-api'),
    path('painel/session', painel_session_api, name='painel-session-api'),
    path('painel/login', painel_login_api, name='painel-login-api'),
    path('painel/logout', painel_logout_api, name='painel-logout-api'),
    path('painel/orders/<int:order_id>', painel_order_detail_api, name='painel-order-detail-api'),
    path('painel/sellers', painel_sellers_api, name='painel-sellers-api'),
    path('painel/payouts', painel_payouts_api, name='painel-payouts-api'),
    path('painel/finance', painel_finance_api, name='painel-finance-api'),
    path('painel/invoices', painel_invoices_api, name='painel-invoices-api'),
]
