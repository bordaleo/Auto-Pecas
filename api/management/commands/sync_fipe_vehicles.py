"""Sincroniza marcas e modelos via API FIPE (Parallelum)."""
from django.core.management.base import BaseCommand

from api.models import VehicleBrand
from api.services.fipe_sync_service import sync_fipe_vehicles


class Command(BaseCommand):
    help = 'Importa marcas e modelos de carros da tabela FIPE (API Parallelum)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-brands',
            type=int,
            default=50,
            help='Número máximo de marcas FIPE a importar (padrão: 50)',
        )

    def handle(self, *args, **options):
        before = VehicleBrand.objects.filter(is_active=True).count()
        result = sync_fipe_vehicles(max_brands=options['max_brands'])
        if result.get('error'):
            self.stderr.write(self.style.ERROR(result['error']))
            return
        self.stdout.write(self.style.SUCCESS(
            f'FIPE: {result["brands_created"]} marcas novas, '
            f'{result["models_created"]} modelos novos, '
            f'{result["models_updated"]} atualizados. '
            f'Total: {result["brands_total"]} marcas, {result["models_total"]} modelos '
            f'(antes: {before} marcas).'
        ))
