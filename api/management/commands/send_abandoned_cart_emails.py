import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from api.services.abandoned_cart_service import get_carts_pending_reminder
from api.services.email_service import email_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Envia e-mails de recuperação para carrinhos abandonados.'

    def add_arguments(self, parser):
        parser.add_argument('--hours', type=int, default=1, help='Horas desde a última atualização')

    def handle(self, *args, **options):
        hours = options['hours']
        carts = get_carts_pending_reminder(hours=hours)
        sent = 0
        for cart in carts:
            if email_service.send_abandoned_cart_email(cart):
                cart.reminder_sent_at = timezone.now()
                cart.save(update_fields=['reminder_sent_at'])
                sent += 1
        self.stdout.write(self.style.SUCCESS(f'Lembretes enviados: {sent}/{carts.count()}'))
