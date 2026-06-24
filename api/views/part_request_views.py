"""Pedidos de peça — demanda pública entre compradores e vendedores."""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from api.models import (
    PartRequest, PartRequestConversation, PartRequestMessage, PartRequestRating,
    PartRequestStatus, Product, Seller,
)
from api.permissions.seller import IsActiveSeller, get_seller_for_user
from api.serializers.part_request import (
    PartRequestCreateSerializer, PartRequestSerializer, PartRequestCloseSerializer,
    PartRequestRespondSerializer, PartRequestConversationSerializer,
    PartRequestMessageSerializer, PartRequestRatingSerializer,
)
from api.serializers.product import ProductListSerializer
from api.services.notification_service import notify_part_request_new, notify_part_request_response
from api.services.part_request_service import (
    MAX_OPEN_REQUESTS, EXPIRY_DAYS, build_quote_message, count_open_requests,
    enrich_vehicle_from_lookup, expire_old_part_requests, find_matching_sellers,
    get_part_request_admin_metrics, get_seller_part_request_stats, seller_match_score,
    sort_requests_for_seller, suggest_products, zip_proximity_score,
)


def _annotate_responses(qs):
    return qs.annotate(response_count=Count('conversations', distinct=True))


class PartRequestSuggestionsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        products = suggest_products(
            q=request.query_params.get('q', '').strip(),
            vehicle_brand=request.query_params.get('vehicle_brand', '').strip(),
            vehicle_model=request.query_params.get('vehicle_model', '').strip(),
            vehicle_year=request.query_params.get('vehicle_year', '').strip(),
        )
        return Response({'products': ProductListSerializer(products, many=True).data})


class PartRequestListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        expire_old_part_requests()
        qs = _annotate_responses(
            PartRequest.objects.filter(requester=request.user),
        )
        return Response(PartRequestSerializer(qs, many=True).data)

    def post(self, request):
        expire_old_part_requests()
        if count_open_requests(request.user) >= MAX_OPEN_REQUESTS:
            return Response(
                {'detail': f'Você já tem {MAX_OPEN_REQUESTS} pedidos abertos. Encerre um antes de criar outro.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = PartRequestCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data
        phone = (data.get('contact_phone') or '').strip() or (request.user.phone or '').strip()
        requester_zip = (request.user.shipping_zip or '').strip()

        part_request = PartRequest(
            requester=request.user,
            description=data['description'].strip(),
            vehicle_brand=(data.get('vehicle_brand') or '').strip(),
            vehicle_model=(data.get('vehicle_model') or '').strip(),
            vehicle_year=data.get('vehicle_year'),
            plate=(data.get('plate') or '').strip().upper(),
            vin=(data.get('vin') or '').strip().upper(),
            contact_phone=phone,
            show_phone=data.get('show_phone', True),
            requester_zip=requester_zip,
            expires_at=timezone.now() + timedelta(days=EXPIRY_DAYS),
        )
        enrich_vehicle_from_lookup(
            part_request,
            plate=part_request.plate,
            vin=part_request.vin,
            query=(data.get('vehicle_query') or '').strip(),
            year=data.get('vehicle_year'),
        )
        part_request.save()
        notify_part_request_new(part_request)
        return Response(
            PartRequestSerializer(_annotate_responses(PartRequest.objects.filter(pk=part_request.pk)).first()).data,
            status=status.HTTP_201_CREATED,
        )


class PartRequestDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_own(self, request, pk):
        try:
            return _annotate_responses(
                PartRequest.objects.filter(requester=request.user, pk=pk),
            ).get()
        except PartRequest.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_own(request, pk)
        if not obj:
            return Response({'detail': 'Pedido não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PartRequestSerializer(obj).data)

    def patch(self, request, pk):
        obj = self._get_own(request, pk)
        if not obj:
            return Response({'detail': 'Pedido não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        ser = PartRequestCloseSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        obj.status = ser.validated_data['status']
        obj.closed_at = timezone.now()
        obj.save(update_fields=['status', 'closed_at'])
        return Response(PartRequestSerializer(obj).data)


class SellerPartRequestStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get(self, request):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        return Response(get_seller_part_request_stats(seller))


class SellerPartRequestListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get(self, request):
        expire_old_part_requests()
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        qs = _annotate_responses(
            PartRequest.objects.filter(status=PartRequestStatus.OPEN)
            .exclude(requester_id=seller.user_id),
        )
        responded_ids = set(
            PartRequestConversation.objects.filter(seller=seller).values_list('part_request_id', flat=True),
        )
        seller_zip = seller.origin_zip or seller.user.shipping_zip or ''
        data = []
        for obj in qs:
            item = PartRequestSerializer(obj).data
            item['already_responded'] = obj.id in responded_ids
            item['match_score'] = seller_match_score(seller, obj)
            item['proximity_score'] = zip_proximity_score(seller_zip, obj.requester_zip or '')
            data.append(item)
        data = sort_requests_for_seller(data, seller)
        return Response(data)


class PartRequestRespondView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def post(self, request, pk):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        try:
            part_request = PartRequest.objects.get(pk=pk, status=PartRequestStatus.OPEN)
        except PartRequest.DoesNotExist:
            return Response({'detail': 'Pedido não encontrado ou encerrado.'}, status=status.HTTP_404_NOT_FOUND)
        if part_request.requester_id == request.user.id:
            return Response({'detail': 'Você não pode responder ao seu próprio pedido.'}, status=status.HTTP_400_BAD_REQUEST)

        ser = PartRequestRespondSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        data = ser.validated_data

        quote_product = None
        if data.get('quote_product_id'):
            quote_product = Product.objects.filter(pk=data['quote_product_id'], seller=seller, is_active=True).first()
            if not quote_product:
                return Response({'detail': 'Peça não encontrada na sua loja.'}, status=status.HTTP_400_BAD_REQUEST)

        conv, created = PartRequestConversation.objects.get_or_create(
            part_request=part_request,
            seller=seller,
            defaults={'buyer': part_request.requester},
        )
        conv.quote_price = data.get('quote_price')
        conv.quote_condition = (data.get('quote_condition') or '').strip()
        conv.quote_delivery_days = data.get('quote_delivery_days')
        conv.quote_product = quote_product
        conv.quote_notes = (data.get('quote_notes') or '').strip()
        conv.save()

        msg_text = (data.get('message') or '').strip()
        if not msg_text and (conv.quote_price or conv.quote_condition):
            msg_text = build_quote_message(conv, seller)
        elif not msg_text:
            msg_text = f'Olá! Tenho essa peça — {seller.store_name}.'

        PartRequestMessage.objects.create(conversation=conv, sender=request.user, body=msg_text)
        conv.last_message_at = timezone.now()
        conv.save(update_fields=['last_message_at'])

        if created:
            notify_part_request_response(part_request, seller)

        conv = PartRequestConversation.objects.select_related(
            'part_request', 'seller', 'buyer', 'quote_product',
        ).get(pk=conv.pk)
        return Response(
            PartRequestConversationSerializer(conv, context={'request': request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PartRequestRateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, conv_id):
        try:
            conv = PartRequestConversation.objects.select_related('part_request').get(
                pk=conv_id, buyer=request.user,
            )
        except PartRequestConversation.DoesNotExist:
            return Response({'detail': 'Conversa não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if conv.part_request.status not in (PartRequestStatus.FULFILLED, PartRequestStatus.CLOSED):
            return Response({'detail': 'Avalie após encerrar ou marcar o pedido como atendido.'}, status=status.HTTP_400_BAD_REQUEST)
        if hasattr(conv, 'rating'):
            return Response({'detail': 'Você já avaliou este atendimento.'}, status=status.HTTP_400_BAD_REQUEST)

        ser = PartRequestRatingSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        rating = PartRequestRating.objects.create(
            conversation=conv,
            rating=ser.validated_data['rating'],
            comment=(ser.validated_data.get('comment') or '').strip(),
        )
        return Response({'rating': rating.rating, 'comment': rating.comment}, status=status.HTTP_201_CREATED)


class PartRequestConversationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        seller = get_seller_for_user(request.user)
        if seller and seller.status == Seller.Status.ACTIVE:
            qs = PartRequestConversation.objects.filter(seller=seller)
        else:
            qs = PartRequestConversation.objects.filter(buyer=request.user)
        qs = qs.select_related(
            'part_request', 'seller', 'buyer', 'quote_product', 'rating',
        ).order_by('-last_message_at')
        return Response(PartRequestConversationSerializer(qs, many=True, context={'request': request}).data)


class PartRequestChatMessagesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_conversation(self, request, conv_id):
        seller = get_seller_for_user(request.user)
        qs = PartRequestConversation.objects.select_related('part_request', 'seller', 'buyer')
        if seller and seller.status == Seller.Status.ACTIVE:
            qs = qs.filter(pk=conv_id, seller=seller)
        else:
            qs = qs.filter(pk=conv_id, buyer=request.user)
        try:
            return qs.get()
        except PartRequestConversation.DoesNotExist:
            return None

    def get(self, request, conv_id):
        conv = self._get_conversation(request, conv_id)
        if not conv:
            return Response({'detail': 'Conversa não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        msgs = conv.messages.select_related('sender').order_by('created_at')
        return Response(PartRequestMessageSerializer(msgs, many=True, context={'request': request}).data)

    def post(self, request, conv_id):
        conv = self._get_conversation(request, conv_id)
        if not conv:
            return Response({'detail': 'Conversa não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        if conv.part_request.status != PartRequestStatus.OPEN:
            return Response({'detail': 'Este pedido foi encerrado.'}, status=status.HTTP_400_BAD_REQUEST)
        from api.serializers.marketplace import ChatMessageCreateSerializer
        ser = ChatMessageCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        msg = PartRequestMessage.objects.create(
            conversation=conv,
            sender=request.user,
            body=ser.validated_data['body'],
        )
        conv.last_message_at = timezone.now()
        conv.save(update_fields=['last_message_at'])
        recipient = conv.buyer if request.user_id == conv.seller.user_id else conv.seller.user
        if recipient.id != request.user.id:
            from api.services.notification_service import notify_part_request_message
            notify_part_request_message(recipient, conv.part_request, request.user.name)
        return Response(
            PartRequestMessageSerializer(msg, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
