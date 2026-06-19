"""Notificações, NF-e, VIN/placa, CSV import, analytics."""
from decimal import Decimal

from django.db.models import F
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import (
    InvoiceRequest, InvoiceStatus, Order, OrderStatus, Product,
    UserNotification, Seller,
)
from api.permissions.seller import IsActiveSeller, get_seller_for_user
from api.serializers.product import ProductListSerializer
from api.services.analytics_service import get_seller_analytics
from api.services.csv_import_service import parse_csv_content, import_products_for_seller
from api.services.notification_service import notify_invoice_issued
from api.services.vin_lookup_service import (
    decode_vin, lookup_plate, find_products_for_vehicle, parse_vehicle_text_query,
)
from api.views.admin_views import painel_api_authorized


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:50]
        unread = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({
            'unread_count': unread,
            'results': [
                {
                    'id': n.id,
                    'type': n.notification_type,
                    'title': n.title,
                    'body': n.body,
                    'link': n.link,
                    'is_read': n.is_read,
                    'created_at': n.created_at.isoformat(),
                }
                for n in qs
            ],
        })

    def patch(self, request):
        ids = request.data.get('ids') or []
        if request.data.get('mark_all'):
            UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        elif ids:
            UserNotification.objects.filter(user=request.user, id__in=ids).update(is_read=True)
        unread = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': unread})


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = UserNotification.objects.filter(user=request.user, is_read=False).count()
        return Response({'unread_count': count})


class VehicleLookupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        vin = (request.data.get('vin') or '').strip()
        plate = (request.data.get('plate') or '').strip()
        query = (request.data.get('query') or '').strip()
        year_override = request.data.get('year')

        if vin:
            result = decode_vin(vin, year_override=year_override)
        elif plate:
            result = lookup_plate(plate, year_override=year_override)
        elif query:
            result = parse_vehicle_text_query(query, year_override=year_override)
        else:
            return Response({'detail': 'Informe VIN, placa ou modelo/ano.'}, status=status.HTTP_400_BAD_REQUEST)

        if not result.get('valid', True):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        model_ids = [m['id'] for m in result.get('vehicle_models', [])]
        products = find_products_for_vehicle(
            model_ids,
            brand_hint=result.get('brand_hint') or '',
            model_hint=result.get('model_hint') or '',
        ) if model_ids or result.get('model_hint') or result.get('brand_hint') else []

        return Response({
            **result,
            'products': ProductListSerializer(products, many=True).data,
        })


class InvoiceRequestListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _serialize_invoice(self, r):
        return {
            'id': r.id,
            'order_id': r.order_id,
            'user_email': r.user.email,
            'seller_name': r.seller.store_name if r.seller_id else 'Galelugi Peças',
            'cnpj': r.cnpj,
            'company_name': r.company_name,
            'company_email': r.company_email,
            'status': r.status,
            'status_display': r.get_status_display(),
            'invoice_number': r.invoice_number,
            'invoice_url': r.invoice_url,
            'admin_notes': r.admin_notes,
            'created_at': r.created_at.isoformat(),
        }

    def get(self, request):
        scope = (request.query_params.get('scope') or '').strip()
        if scope == 'manage':
            seller = get_seller_for_user(request.user)
            is_admin = request.user.is_staff or painel_api_authorized(request)
            if is_admin:
                qs = InvoiceRequest.objects.select_related('order', 'user', 'seller')
            elif seller:
                qs = InvoiceRequest.objects.filter(seller=seller).select_related('order', 'user', 'seller')
            else:
                return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            qs = InvoiceRequest.objects.filter(user=request.user).select_related('order', 'user', 'seller')
        return Response([self._serialize_invoice(r) for r in qs.order_by('-created_at')[:100]])

    def post(self, request):
        order_id = request.data.get('order_id')
        try:
            order = Order.objects.get(pk=order_id, user=request.user, status=OrderStatus.APPROVED)
        except Order.DoesNotExist:
            return Response({'detail': 'Pedido não encontrado ou não pago.'}, status=status.HTTP_404_NOT_FOUND)

        if InvoiceRequest.objects.filter(order=order, status__in=[
            InvoiceStatus.REQUESTED, InvoiceStatus.PROCESSING, InvoiceStatus.ISSUED,
        ]).exists():
            return Response({'detail': 'NF-e já solicitada para este pedido.'}, status=status.HTTP_400_BAD_REQUEST)

        cnpj = (request.data.get('cnpj') or '').strip()
        company_name = (request.data.get('company_name') or '').strip()
        if not cnpj or not company_name:
            return Response({'detail': 'CNPJ e razão social são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

        inv = InvoiceRequest.objects.create(
            order=order,
            user=request.user,
            seller=order.fulfillment_seller,
            cnpj=cnpj,
            company_name=company_name,
            company_email=request.data.get('company_email') or request.user.email,
        )
        return Response({'id': inv.id, 'status': inv.status}, status=status.HTTP_201_CREATED)


class InvoiceRequestManageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            inv = InvoiceRequest.objects.select_related('order', 'user').get(pk=pk)
        except InvoiceRequest.DoesNotExist:
            return Response({'detail': 'Não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        seller = get_seller_for_user(request.user)
        is_admin = request.user.is_staff or painel_api_authorized(request)
        if not is_admin and (not seller or inv.seller_id != seller.id):
            return Response({'detail': 'Sem permissão.'}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        if new_status in dict(InvoiceStatus.choices):
            inv.status = new_status
        if request.data.get('invoice_number'):
            inv.invoice_number = request.data['invoice_number']
        if request.data.get('invoice_url'):
            inv.invoice_url = request.data['invoice_url']
        if request.data.get('admin_notes'):
            inv.admin_notes = request.data['admin_notes']
        inv.save()

        if inv.status == InvoiceStatus.ISSUED:
            notify_invoice_issued(inv.user, inv)

        return Response({'id': inv.id, 'status': inv.status})


class SellerAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]

    def get(self, request):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        days = int(request.query_params.get('days', 30))
        return Response(get_seller_analytics(seller, days=days))


class SellerCsvImportView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveSeller]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        seller = Seller.objects.get(user=request.user, status=Seller.Status.ACTIVE)
        upload = request.FILES.get('file')
        if not upload:
            text = request.data.get('csv', '')
        else:
            text = upload.read().decode('utf-8-sig', errors='replace')

        if not text.strip():
            return Response({'detail': 'Envie um arquivo CSV.'}, status=status.HTTP_400_BAD_REQUEST)

        rows, parse_errors = parse_csv_content(text)
        if parse_errors:
            return Response({'detail': parse_errors[0], 'errors': parse_errors}, status=status.HTTP_400_BAD_REQUEST)

        created, import_errors = import_products_for_seller(seller, request.user, rows)
        return Response({
            'created': created,
            'errors': import_errors,
            'template_columns': sorted({
                'name', 'price', 'stock', 'image_url', 'description', 'sku', 'oem_code',
                'brand', 'compatible_vehicles', 'part_condition', 'part_origin',
                'warranty_days', 'category_slug',
            }),
        })


class SellerCsvTemplateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'columns': [
                'name', 'price', 'stock', 'image_url', 'description', 'sku', 'oem_code',
                'brand', 'compatible_vehicles', 'part_condition', 'part_origin',
                'warranty_days', 'category_slug',
            ],
            'required': ['name', 'price', 'stock', 'image_url'],
            'example': (
                'name,price,stock,image_url,sku,brand,part_condition,part_origin,warranty_days\n'
                'Farol Gol G6,450.00,2,https://exemplo.com/farol.jpg,FAR-GOL-001,VW,new,original,90'
            ),
        })
