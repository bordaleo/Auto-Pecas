from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import Coupon, Order, OrderGroup, OrderItem, OrderStatus, Product, Seller, User
from api.services.payment_service import payment_service

SHIPPING_FEE = Decimal('10.00')
PREFERENCE_ID = 'pref-123'


@override_settings(OPS_ALERT_WEBHOOK_URL='', OPS_ALERT_EMAIL='')
class MultiSellerPaymentFlowTests(TestCase):
    """Checkout com duas lojas, pagamento via Payment Brick, webhook e polling."""

    def setUp(self):
        self.buyer = User.objects.create_user('comprador@example.com', 'senha-forte-123', name='Comprador')
        self.seller_a = self._make_seller('loja-a')
        self.seller_b = self._make_seller('loja-b')
        self.product_a = Product.objects.create(
            name='Pastilha de freio', slug='pastilha', price=Decimal('100.00'), stock=5, seller=self.seller_a,
        )
        self.product_b = Product.objects.create(
            name='Filtro de óleo', slug='filtro', price=Decimal('50.00'), stock=3, seller=self.seller_b,
        )

        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

        self._patch(
            'api.services.checkout_service.calculate_group_shipping',
            return_value=(SHIPPING_FEE, None, None, {'service_name': 'PAC', 'days': 5, 'provider': 'fixed'}),
        )
        self._patch_object(payment_service, 'create_shop_payment_preference', return_value={'id': PREFERENCE_ID})
        self.create_payment = self._patch_object(payment_service, 'create_payment')
        self.get_payment = self._patch_object(payment_service, 'get_payment')
        self.send_notifications = self._patch('api.services.order_payment_service._send_paid_notifications')

    def _patch(self, target, **kwargs):
        patcher = mock.patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def _patch_object(self, obj, attr, **kwargs):
        patcher = mock.patch.object(obj, attr, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def _make_seller(self, slug):
        user = User.objects.create_user(f'{slug}@example.com', 'senha-forte-123', name=slug)
        return Seller.objects.create(user=user, store_name=slug, slug=slug, status=Seller.Status.ACTIVE)

    def _checkout(self, coupon_code=''):
        response = self.client.post('/api/v1/shop/checkout/', {
            'items': [
                {'product_id': self.product_a.id, 'quantity': 1},
                {'product_id': self.product_b.id, 'quantity': 1},
            ],
            'customer_name': 'Comprador',
            'delivery_method': 'delivery',
            'shipping_zip': '01001000',
            'shipping_address': 'Praça da Sé, 1',
            'shipping_city': 'São Paulo',
            'shipping_state': 'SP',
            'coupon_code': coupon_code,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.post(
            '/api/v1/shop/payment/preference/', {'order_id': response.data['id']}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        return OrderGroup.objects.get(pk=response.data['order_group_id'])

    def _process_payment(self, mp_payment):
        self.create_payment.return_value = mp_payment
        return self.client.post('/api/v1/payments/process', {
            'preference_id': PREFERENCE_ID,
            'form_data': {'token': 'card-token', 'payment_method_id': 'visa'},
        }, format='json')

    def _webhook(self, group, payment_id, mp_status):
        self.get_payment.return_value = {
            'id': payment_id,
            'status': mp_status,
            'payment_method_id': 'visa',
            'external_reference': f'group_{group.id}_user_{self.buyer.id}',
        }
        return APIClient().post(
            '/api/v1/payments/webhook', {'type': 'payment', 'data': {'id': str(payment_id)}}, format='json',
        )

    def _assert_group_status(self, group, expected):
        group.refresh_from_db()
        self.assertEqual(group.status, expected)
        self.assertEqual(
            set(group.orders.values_list('status', flat=True)), {expected},
        )

    def _seller_balance(self, seller):
        seller.refresh_from_db()
        return seller.balance_available

    def _expected_earning(self, seller):
        return sum(OrderItem.objects.filter(seller=seller).values_list('seller_earning', flat=True))

    def test_brick_payment_charges_group_total_and_approves_every_sub_order(self):
        group = self._checkout()
        self.assertEqual(group.orders.count(), 2)
        self.assertEqual(group.amount, Decimal('150.00') + 2 * SHIPPING_FEE)

        with self.captureOnCommitCallbacks(execute=True):
            response = self._process_payment({'id': 999, 'status': 'approved', 'payment_method_id': 'visa'})

        self.assertEqual(response.status_code, 200, response.data)
        sent = self.create_payment.call_args.args[0]
        self.assertEqual(sent['transaction_amount'], float(group.amount))
        self.assertEqual(sent['external_reference'], f'group_{group.id}_user_{self.buyer.id}')

        self._assert_group_status(group, OrderStatus.APPROVED)
        self.assertEqual(set(group.orders.values_list('payment_id', flat=True)), {'999'})
        self.product_a.refresh_from_db()
        self.product_b.refresh_from_db()
        self.assertEqual((self.product_a.stock, self.product_b.stock), (4, 2))
        self.assertEqual(self._seller_balance(self.seller_a), self._expected_earning(self.seller_a))
        self.assertEqual(self._seller_balance(self.seller_b), self._expected_earning(self.seller_b))
        self.send_notifications.assert_called_once()

    def test_pix_status_polling_works_for_multi_seller_group(self):
        group = self._checkout()
        response = self._process_payment({
            'id': 999,
            'status': 'pending',
            'payment_method_id': 'pix',
            'point_of_interaction': {'transaction_data': {'qr_code': 'pix-copia-e-cola'}},
        })
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['pix_qr_code'], 'pix-copia-e-cola')
        self._assert_group_status(group, OrderStatus.PENDING)

        self.get_payment.return_value = {'id': 999, 'status': 'approved', 'payment_method_id': 'pix'}
        response = self.client.get(f'/api/v1/payments/status/{PREFERENCE_ID}')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], OrderStatus.APPROVED)
        self.assertEqual(Decimal(str(response.data['amount'])), group.amount)
        self._assert_group_status(group, OrderStatus.APPROVED)

    def test_repeated_approval_does_not_double_decrement_stock_or_credit_sellers(self):
        group = self._checkout()
        with self.captureOnCommitCallbacks(execute=True):
            self._process_payment({'id': 999, 'status': 'approved', 'payment_method_id': 'visa'})
            self._webhook(group, 999, 'approved')
            self._webhook(group, 999, 'approved')
            self.get_payment.return_value = {'id': 999, 'status': 'approved'}
            self.client.get(f'/api/v1/payments/status/{PREFERENCE_ID}')

        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 4)
        self.assertEqual(self._seller_balance(self.seller_a), self._expected_earning(self.seller_a))
        self.send_notifications.assert_called_once()

    def test_late_rejected_payment_does_not_undo_paid_order(self):
        group = self._checkout()
        self._process_payment({'id': 999, 'status': 'approved', 'payment_method_id': 'visa'})

        response = self._webhook(group, 1000, 'rejected')

        self.assertEqual(response.status_code, 200)
        self._assert_group_status(group, OrderStatus.APPROVED)
        self.assertEqual(set(group.orders.values_list('payment_id', flat=True)), {'999'})

    def test_refund_of_paid_order_keeps_it_approved_and_raises_alert(self):
        group = self._checkout()
        self._process_payment({'id': 999, 'status': 'approved', 'payment_method_id': 'visa'})

        with self.assertLogs('api.services.order_payment_service', level='ERROR') as logs:
            self._webhook(group, 999, 'refunded')

        self._assert_group_status(group, OrderStatus.APPROVED)
        self.assertIn('refunded', logs.output[0])
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 4)

    def test_rejected_card_then_approved_retry(self):
        group = self._checkout()

        self._process_payment({'id': 998, 'status': 'rejected', 'payment_method_id': 'visa'})
        self._assert_group_status(group, OrderStatus.REJECTED)

        self._process_payment({'id': 999, 'status': 'approved', 'payment_method_id': 'master'})
        self._assert_group_status(group, OrderStatus.APPROVED)
        self.product_b.refresh_from_db()
        self.assertEqual(self.product_b.stock, 2)

    def test_coupon_usage_is_counted_once_on_payment_not_on_checkout(self):
        coupon = Coupon.objects.create(code='BEMVINDO', discount_type='fixed', discount_value=Decimal('20.00'))
        group = self._checkout(coupon_code='bemvindo')
        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 0)
        self.assertEqual(group.amount, Decimal('150.00') + 2 * SHIPPING_FEE - Decimal('20.00'))

        self._process_payment({'id': 999, 'status': 'approved', 'payment_method_id': 'visa'})
        self._webhook(group, 999, 'approved')

        coupon.refresh_from_db()
        self.assertEqual(coupon.used_count, 1)
        sent = self.create_payment.call_args.args[0]
        self.assertEqual(sent['transaction_amount'], float(group.amount))

    def test_single_seller_order_still_works(self):
        response = self.client.post('/api/v1/shop/checkout/', {
            'items': [{'product_id': self.product_a.id, 'quantity': 2}],
            'customer_name': 'Comprador',
            'delivery_method': 'pickup',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.client.post('/api/v1/shop/payment/preference/', {'order_id': response.data['id']}, format='json')

        response = self._process_payment({'id': 999, 'status': 'approved', 'payment_method_id': 'visa'})

        self.assertEqual(response.status_code, 200, response.data)
        order = Order.objects.get(payment_id='999')
        self.assertEqual(order.status, OrderStatus.APPROVED)
        self.assertEqual(self.create_payment.call_args.args[0]['transaction_amount'], float(order.amount))
        self.product_a.refresh_from_db()
        self.assertEqual(self.product_a.stock, 3)
