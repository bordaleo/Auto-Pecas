"""Popula marcas e modelos de veículos comuns no Brasil."""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from api.models import VehicleBrand, VehicleModel


VEHICLES = [
    ('Volkswagen', [
        ('Gol', 2008, 2024),
        ('Polo', 2010, 2026),
        ('Virtus', 2018, 2024),
        ('T-Cross', 2019, 2024),
        ('Amarok', 2010, 2024),
    ]),
    ('Fiat', [
        ('Uno', 2010, 2024),
        ('Palio', 2010, 2017),
        ('Argo', 2017, 2024),
        ('Cronos', 2018, 2024),
        ('Strada', 2010, 2024),
        ('Toro', 2016, 2024),
    ]),
    ('Chevrolet', [
        ('Onix', 2012, 2024),
        ('Prisma', 2013, 2019),
        ('Tracker', 2020, 2024),
        ('S10', 2010, 2024),
        ('Cruze', 2011, 2023),
    ]),
    ('Ford', [
        ('Ka', 2010, 2021),
        ('Fiesta', 2010, 2019),
        ('EcoSport', 2010, 2022),
        ('Ranger', 2010, 2024),
        ('Focus', 2010, 2019),
    ]),
    ('Hyundai', [
        ('HB20', 2012, 2024),
        ('Creta', 2017, 2024),
        ('Tucson', 2010, 2024),
    ]),
    ('Toyota', [
        ('Corolla', 2010, 2024),
        ('Hilux', 2010, 2024),
        ('Yaris', 2018, 2024),
    ]),
    ('Honda', [
        ('Civic', 2010, 2024),
        ('City', 2010, 2024),
        ('HR-V', 2015, 2024),
        ('Fit', 2010, 2020),
    ]),
    ('Renault', [
        ('Sandero', 2010, 2024),
        ('Logan', 2010, 2024),
        ('Duster', 2011, 2024),
        ('Kwid', 2017, 2024),
    ]),
    ('Jeep', [
        ('Renegade', 2015, 2024),
        ('Compass', 2017, 2024),
    ]),
    ('Nissan', [
        ('March', 2011, 2024),
        ('Kicks', 2017, 2024),
        ('Frontier', 2010, 2024),
    ]),
]


class Command(BaseCommand):
    help = 'Cadastra marcas e modelos de veículos para filtro de compatibilidade'

    def handle(self, *args, **options):
        created_brands = 0
        created_models = 0
        for brand_name, models in VEHICLES:
            slug = slugify(brand_name)
            brand, b_created = VehicleBrand.objects.get_or_create(
                slug=slug,
                defaults={'name': brand_name, 'is_active': True},
            )
            if b_created:
                created_brands += 1
            for model_name, y_start, y_end in models:
                mslug = slugify(model_name)
                _, m_created = VehicleModel.objects.get_or_create(
                    brand=brand,
                    slug=mslug,
                    defaults={
                        'name': model_name,
                        'year_start': y_start,
                        'year_end': y_end,
                        'is_active': True,
                    },
                )
                if m_created:
                    created_models += 1
        self.stdout.write(self.style.SUCCESS(
            f'Veículos: {created_brands} marcas e {created_models} modelos criados.'
        ))
