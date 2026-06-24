from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import PartRequest, PartRequestStatus
from api.services.part_request_service import EXPIRY_DAYS, expire_old_part_requests


class Command(BaseCommand):
    help = 'Encerra pedidos de peça abertos há mais de 14 dias.'

    def handle(self, *args, **options):
        count = expire_old_part_requests()
        self.stdout.write(self.style.SUCCESS(f'{count} pedido(s) encerrado(s) por expiração.'))

        # Preenche expires_at em pedidos antigos sem data
        missing = PartRequest.objects.filter(status=PartRequestStatus.OPEN, expires_at__isnull=True)
        updated = 0
        for req in missing.iterator():
            req.expires_at = req.created_at + timedelta(days=EXPIRY_DAYS)
            req.save(update_fields=['expires_at'])
            updated += 1
        if updated:
            self.stdout.write(f'{updated} pedido(s) receberam data de expiração.')
