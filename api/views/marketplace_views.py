"""Views: repasses, pedidos vendedor, avaliações, veículos, devoluções, chat."""
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.models import (
    OrderItem, OrderStatus, Product, ProductConversation, ProductMessage,
    ProductReview, ReturnRequest, ReturnStatus, Seller, SellerPayout, ShippingStatus,
    SystemConfig, VehicleBrand, VehicleModel,
)
from api.permissions.seller import IsActiveSeller, get_seller_for_user
from api.serializers.marketplace import (
    SellerPayoutSerializer, PayoutRequestSerializer, SellerPixKeySerializer,
    SellerOrderItemSerializer, SellerShippingUpdateSerializer,
    ProductReviewSerializer, ProductReviewCreateSerializer,
    VehicleBrandListSerializer, VehicleModelSerializer, VehicleBrandSerializer,
    ProductVehicleCompatWriteSerializer,
    ReturnRequestSerializer, ReturnRequestCreateSerializer, ReturnStatusUpdateSerializer,
    ProductConversationSerializer, ProductMessageSerializer,
    ChatMessageCreateSerializer, ChatStartSerializer,
)
from api.services.payout_service import (
    request_payout, process_payout, seller_payout_summary, debit_seller_for_return,
)
from api.services.notification_service import (
    notify_payout_paid, notify_return_opened, notify_return_approved,
    notify_chat_message, notify_buyer_shipped,
)
from api.views.admin_views import painel_api_authorized


class SellerPayoutSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get(self, request):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        data = seller_payout_summary(seller)
        payouts = SellerPayout.objects.filter(seller=seller).order_by('-created_at')[:20]
        data['payouts'] = SellerPayoutSerializer(payouts, many=True).data
        return Response(data)

    def patch(self, request):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        ser = SellerPixKeySerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        seller.pix_key = ser.validated_data['pix_key']
        seller.save(update_fields=['pix_key', 'updated_at'])
        return Response(seller_payout_summary(seller))


class SellerPayoutRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def post(self, request):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        ser = PayoutRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            payout = request_payout(
                seller,
                ser.validated_data['amount'],
                ser.validated_data.get('pix_key', ''),
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SellerPayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class SellerOrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get(self, request):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        qs = (
            OrderItem.objects.filter(seller=seller, order__status=OrderStatus.APPROVED)
            .select_related('order')
            .order_by('-order__created_at')
        )
        status_filter = request.query_params.get('shipping_status', '').strip()
        if status_filter:
            qs = qs.filter(item_shipping_status=status_filter)
        return Response(SellerOrderItemSerializer(qs[:100], many=True).data)


class SellerOrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get(self, request, item_id):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        try:
            item = OrderItem.objects.select_related('order').get(
                pk=item_id, seller=seller, order__status=OrderStatus.APPROVED,
            )
        except OrderItem.DoesNotExist:
            return Response({'detail': 'Item não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SellerOrderItemSerializer(item).data)

    def patch(self, request, item_id):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        try:
            item = OrderItem.objects.select_related('order').get(
                pk=item_id, seller=seller, order__status=OrderStatus.APPROVED,
            )
        except OrderItem.DoesNotExist:
            return Response({'detail': 'Item não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        ser = SellerShippingUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data
        if 'item_shipping_status' in data:
            item.item_shipping_status = data['item_shipping_status']
            if data['item_shipping_status'] == ShippingStatus.SHIPPED:
                item.item_shipped_at = timezone.now()
        if 'item_tracking_code' in data:
            item.item_tracking_code = data['item_tracking_code']
        if 'item_carrier' in data:
            item.item_carrier = data['item_carrier']
        item.save()
        if data.get('item_shipping_status') == ShippingStatus.SHIPPED:
            notify_buyer_shipped(item.order, item.item_tracking_code)
        return Response(SellerOrderItemSerializer(item).data)


class ProductReviewListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        try:
            product = Product.objects.get(pk=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        reviews = ProductReview.objects.filter(product=product, is_visible=True).select_related('user')
        stats = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
        return Response({
            'average_rating': round(float(stats['avg'] or 0), 1),
            'review_count': stats['count'] or 0,
            'reviews': ProductReviewSerializer(reviews[:50], many=True).data,
        })


class ProductReviewCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ProductReviewCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data
        try:
            product = Product.objects.get(pk=data['product_id'], is_active=True)
        except Product.DoesNotExist:
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        order_item = None
        verified = False
        if data.get('order_item_id'):
            try:
                order_item = OrderItem.objects.select_related('order').get(
                    pk=data['order_item_id'],
                    order__user=request.user,
                    order__status=OrderStatus.APPROVED,
                    product=product,
                )
                verified = True
            except OrderItem.DoesNotExist:
                return Response({'detail': 'Item do pedido inválido.'}, status=status.HTTP_400_BAD_REQUEST)

        if ProductReview.objects.filter(
            product=product, user=request.user, order_item=order_item,
        ).exists():
            return Response({'detail': 'Você já avaliou esta compra.'}, status=status.HTTP_400_BAD_REQUEST)

        review = ProductReview.objects.create(
            product=product,
            user=request.user,
            order_item=order_item,
            rating=data['rating'],
            title=data.get('title', ''),
            comment=data.get('comment', ''),
            is_verified_purchase=verified,
        )
        return Response(ProductReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class VehicleBrandListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from api.services.fipe_sync_service import schedule_full_fipe_sync

        from django.db.models import Count, Q

        active_count = VehicleBrand.objects.filter(is_active=True).count()
        if active_count < 20:
            schedule_full_fipe_sync()

        brands = (
            VehicleBrand.objects.filter(is_active=True)
            .annotate(model_count=Count('models', filter=Q(models__is_active=True)))
            .order_by('name')
        )
        return Response(VehicleBrandListSerializer(brands, many=True).data)


def _vehicle_model_queryset(request):
    from django.utils.text import slugify
    from api.services.fipe_sync_service import ensure_brand_models_synced

    brand = request.query_params.get('brand', '').strip()
    year = request.query_params.get('year', '').strip()
    q = request.query_params.get('q', '').strip()

    if brand:
        ensure_brand_models_synced(brand, min_models=12)

    qs = VehicleModel.objects.filter(is_active=True).select_related('brand')
    if brand:
        qs = qs.filter(Q(brand__slug=brand) | Q(brand__name__iexact=brand))
    if year:
        try:
            y = int(year)
            qs = qs.filter(year_start__lte=y, year_end__gte=y)
        except ValueError:
            pass
    if q:
        q_slug = slugify(q)
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(slug__icontains=q_slug)
            | Q(brand__name__icontains=q)
        )
    return qs.order_by('brand__name', 'name')


class VehicleModelListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = _vehicle_model_queryset(request)
        try:
            limit = min(int(request.query_params.get('limit', '1000')), 5000)
        except ValueError:
            limit = 1000
        try:
            offset = max(int(request.query_params.get('offset', '0')), 0)
        except ValueError:
            offset = 0

        total = qs.count()
        page = qs[offset:offset + limit]
        return Response({
            'count': total,
            'results': VehicleModelSerializer(page, many=True).data,
        })


class VehicleSearchView(APIView):
    """Busca textual de modelos em todas as marcas (autocomplete)."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.utils.text import slugify
        from api.services.fipe_sync_service import ensure_brand_models_synced

        q = request.query_params.get('q', '').strip()
        year = request.query_params.get('year', '').strip()
        brand = request.query_params.get('brand', '').strip()

        if len(q) < 2:
            return Response({'count': 0, 'results': []})

        if brand:
            ensure_brand_models_synced(brand, min_models=12)

        qs = VehicleModel.objects.filter(is_active=True).select_related('brand')
        q_slug = slugify(q)
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(slug__icontains=q_slug)
            | Q(brand__name__icontains=q)
        )
        if brand:
            qs = qs.filter(Q(brand__slug=brand) | Q(brand__name__iexact=brand))
        if year:
            try:
                y = int(year)
                qs = qs.filter(year_start__lte=y, year_end__gte=y)
            except ValueError:
                pass

        try:
            limit = min(int(request.query_params.get('limit', '30')), 50)
        except ValueError:
            limit = 30

        results = []
        for vm in qs[: limit * 3]:
            score = 0
            name_l = vm.name.lower()
            q_l = q.lower()
            if name_l == q_l:
                score = 100
            elif name_l.startswith(q_l):
                score = 90
            elif q_l in name_l:
                score = 75
            elif vm.slug == q_slug:
                score = 85
            else:
                score = 60
            results.append((score, vm))

        results.sort(key=lambda x: (-x[0], x[1].brand.name, x[1].name))
        models = [vm for _, vm in results[:limit]]
        return Response({
            'count': len(models),
            'results': VehicleModelSerializer(models, many=True).data,
        })


class ReturnRequestListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = ReturnRequest.objects.filter(user=request.user).select_related('order_item', 'order')
        return Response(ReturnRequestSerializer(qs, many=True).data)

    def post(self, request):
        ser = ReturnRequestCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            item = OrderItem.objects.select_related('order', 'seller').get(
                pk=ser.validated_data['order_item_id'],
                order__user=request.user,
                order__status=OrderStatus.APPROVED,
            )
        except OrderItem.DoesNotExist:
            return Response({'detail': 'Item não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if ReturnRequest.objects.filter(
            order_item=item,
            status__in=[ReturnStatus.REQUESTED, ReturnStatus.APPROVED, ReturnStatus.ITEM_SHIPPED, ReturnStatus.RECEIVED],
        ).exists():
            return Response({'detail': 'Já existe uma devolução aberta para este item.'}, status=status.HTTP_400_BAD_REQUEST)

        ret = ReturnRequest.objects.create(
            order=item.order,
            order_item=item,
            user=request.user,
            seller=item.seller,
            reason=ser.validated_data['reason'],
            description=ser.validated_data.get('description', ''),
        )
        if ret.seller_id:
            notify_return_opened(ret.seller.user, ret)
        return Response(ReturnRequestSerializer(ret).data, status=status.HTTP_201_CREATED)


class ReturnRequestDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return ReturnRequest.objects.select_related('order_item', 'order').get(pk=pk)
        except ReturnRequest.DoesNotExist:
            return None

    def get(self, request, pk):
        ret = self.get_object(request, pk)
        if not ret:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if ret.user_id != request.user.id and not _can_manage_return(request, ret):
            return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(ReturnRequestSerializer(ret).data)

    def patch(self, request, pk):
        ret = self.get_object(request, pk)
        if not ret:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        if not _can_manage_return(request, ret):
            return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)

        ser = ReturnStatusUpdateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data
        new_status = data['status']

        seller = get_seller_for_user(request.user)
        is_seller = seller and ret.seller_id == seller.id
        is_admin = request.user.is_staff or painel_api_authorized(request)

        if is_seller and not is_admin:
            allowed = {
                ReturnStatus.REQUESTED: [ReturnStatus.APPROVED, ReturnStatus.REJECTED],
                ReturnStatus.ITEM_SHIPPED: [ReturnStatus.RECEIVED],
            }
            if new_status not in allowed.get(ret.status, []):
                return Response({'detail': 'Transição de status não permitida.'}, status=status.HTTP_400_BAD_REQUEST)
            if data.get('seller_response'):
                ret.seller_response = data['seller_response']

        if is_admin:
            ret.admin_notes = data.get('admin_notes', ret.admin_notes)
            if data.get('refund_amount') is not None:
                ret.refund_amount = data['refund_amount']
            if new_status == ReturnStatus.REFUNDED and ret.refund_amount and ret.seller_id:
                debit_seller_for_return(ret.seller_id, ret.refund_amount)

        if data.get('return_tracking_code'):
            ret.return_tracking_code = data['return_tracking_code']

        ret.status = new_status
        ret.save()
        if new_status == ReturnStatus.APPROVED:
            notify_return_approved(ret.user, ret)
        return Response(ReturnRequestSerializer(ret).data)


def _can_manage_return(request, ret):
    if request.user.is_staff or painel_api_authorized(request):
        return True
    seller = get_seller_for_user(request.user)
    return seller and ret.seller_id == seller.id


class SellerReturnListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get(self, request):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        qs = ReturnRequest.objects.filter(seller=seller).select_related('order_item', 'order')
        return Response(ReturnRequestSerializer(qs, many=True).data)


class ChatConversationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        seller = get_seller_for_user(request.user)
        if seller and seller.status == Seller.Status.ACTIVE:
            qs = ProductConversation.objects.filter(seller=seller)
        else:
            qs = ProductConversation.objects.filter(buyer=request.user)
        qs = qs.select_related('product', 'seller', 'buyer').order_by('-last_message_at')
        return Response(ProductConversationSerializer(qs, many=True, context={'request': request}).data)


class ChatStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = ChatStartSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            product = Product.objects.select_related('seller').get(
                pk=ser.validated_data['product_id'], is_active=True,
            )
        except Product.DoesNotExist:
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if not product.seller_id:
            return Response({'detail': 'Esta peça não possui vendedor para chat.'}, status=status.HTTP_400_BAD_REQUEST)
        if product.seller.user_id == request.user.id:
            return Response({'detail': 'Você não pode iniciar chat consigo mesmo.'}, status=status.HTTP_400_BAD_REQUEST)

        conv, _ = ProductConversation.objects.get_or_create(
            product=product,
            buyer=request.user,
            defaults={'seller': product.seller},
        )
        msg_text = (ser.validated_data.get('message') or '').strip()
        if msg_text:
            ProductMessage.objects.create(conversation=conv, sender=request.user, body=msg_text)
            conv.last_message_at = timezone.now()
            conv.save(update_fields=['last_message_at'])
        return Response(ProductConversationSerializer(conv, context={'request': request}).data)


class ChatMessagesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_conversation(self, request, conv_id):
        try:
            conv = ProductConversation.objects.select_related('seller', 'buyer').get(pk=conv_id)
        except ProductConversation.DoesNotExist:
            return None
        seller = get_seller_for_user(request.user)
        if conv.buyer_id == request.user.id:
            return conv
        if seller and conv.seller_id == seller.id:
            return conv
        return None

    def get(self, request, conv_id):
        conv = self._get_conversation(request, conv_id)
        if not conv:
            return Response({'detail': 'Conversa não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        msgs = conv.messages.select_related('sender').order_by('created_at')
        conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response(ProductMessageSerializer(msgs, many=True, context={'request': request}).data)

    def post(self, request, conv_id):
        conv = self._get_conversation(request, conv_id)
        if not conv:
            return Response({'detail': 'Conversa não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        ser = ChatMessageCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        msg = ProductMessage.objects.create(
            conversation=conv,
            sender=request.user,
            body=ser.validated_data['body'],
        )
        conv.last_message_at = timezone.now()
        conv.save(update_fields=['last_message_at'])
        recipient = conv.buyer if request.user_id == conv.seller.user_id else conv.seller.user
        if recipient.id != request.user.id:
            notify_chat_message(recipient, conv.product.name, request.user.name)
        return Response(ProductMessageSerializer(msg, context={'request': request}).data, status=status.HTTP_201_CREATED)


class ProductWhatsAppLinkView(APIView):
    """Link WhatsApp direto com vendedor sobre uma peça."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        try:
            product = Product.objects.select_related('seller').get(pk=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({'detail': 'Peça não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if not product.seller_id:
            config_phone = SystemConfig.get_config().store_whatsapp or SystemConfig.get_config().store_phone
            phone = config_phone
            seller_name = 'Galelugi'
        else:
            phone = product.seller.phone or product.seller.user.phone
            seller_name = product.seller.store_name
        digits = ''.join(c for c in (phone or '') if c.isdigit())
        if not digits:
            return Response({'detail': 'Telefone do vendedor não disponível.'}, status=status.HTTP_404_NOT_FOUND)
        if not digits.startswith('55'):
            digits = '55' + digits
        text = f'Olá! Tenho interesse na peça "{product.name}" (SKU: {product.sku or product.slug}) na Galelugi.'
        import urllib.parse
        url = f'https://wa.me/{digits}?text={urllib.parse.quote(text)}'
        return Response({'url': url, 'seller_name': seller_name})
