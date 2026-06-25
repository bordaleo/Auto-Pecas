"""Popula marcas e modelos de veículos comuns no Brasil."""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from api.models import VehicleBrand, VehicleModel


VEHICLES = [
    ('Volkswagen', [
        ('Gol', 2008, 2026),
        ('Polo', 2010, 2026),
        ('Virtus', 2018, 2026),
        ('T-Cross', 2019, 2026),
        ('Amarok', 2010, 2026),
        ('Golf', 2010, 2026),
        ('Jetta', 2010, 2026),
        ('Passat', 2010, 2020),
        ('Fox', 2010, 2021),
        ('Up!', 2014, 2021),
    ]),
    ('Fiat', [
        ('Uno', 2010, 2026),
        ('Palio', 2010, 2017),
        ('Argo', 2017, 2026),
        ('Cronos', 2018, 2026),
        ('Strada', 2010, 2026),
        ('Toro', 2016, 2026),
    ]),
    ('Chevrolet', [
        ('Onix', 2012, 2026),
        ('Prisma', 2013, 2019),
        ('Tracker', 2020, 2026),
        ('S10', 2010, 2026),
        ('Cruze', 2011, 2023),
    ]),
    ('Ford', [
        ('Ka', 2010, 2021),
        ('Fiesta', 2010, 2019),
        ('EcoSport', 2010, 2022),
        ('Ranger', 2010, 2026),
        ('Focus', 2010, 2019),
    ]),
    ('Hyundai', [
        ('HB20', 2012, 2026),
        ('Creta', 2017, 2026),
        ('Tucson', 2010, 2026),
    ]),
    ('Toyota', [
        ('Corolla', 2010, 2026),
        ('Hilux', 2010, 2026),
        ('Yaris', 2018, 2026),
    ]),
    ('Honda', [
        ('Civic', 2010, 2026),
        ('City', 2010, 2026),
        ('HR-V', 2015, 2026),
        ('Fit', 2010, 2020),
    ]),
    ('Renault', [
        ('Sandero', 2010, 2026),
        ('Logan', 2010, 2026),
        ('Duster', 2011, 2026),
        ('Kwid', 2017, 2026),
    ]),
    ('Jeep', [
        ('Renegade', 2015, 2026),
        ('Compass', 2017, 2026),
    ]),
    ('Nissan', [
        ('March', 2011, 2026),
        ('Kicks', 2017, 2026),
        ('Frontier', 2010, 2026),
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
                obj, m_created = VehicleModel.objects.update_or_create(
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
