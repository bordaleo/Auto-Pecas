"""Libera reservas de estoque expiradas (rodar via cron a cada 5 min)."""
from django.core.management.base import BaseCommand
from api.services.stock_reservation_service import release_expired_reservations


class Command(BaseCommand):
    help = 'Libera reservas de estoque expiradas'

    def handle(self, *args, **options):
        count = release_expired_reservations()
        self.stdout.write(self.style.SUCCESS(f'{count} reserva(s) liberada(s).'))
