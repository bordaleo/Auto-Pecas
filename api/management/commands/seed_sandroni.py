from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from api.models import Category, Product, SystemConfig


CATEGORIES = [
    ('motor', 'Motor', '🔩', 'Peças do motor e sistema de ignição'),
    ('freios', 'Freios', '🛑', 'Pastilhas, discos, fluido e componentes'),
    ('suspensao', 'Suspensão', '🔧', 'Amortecedores, molas e buchas'),
    ('filtros', 'Filtros', '🌬', 'Óleo, ar, combustível e cabine'),
    ('eletrica', 'Elétrica', '⚡', 'Alternadores, baterias e sensores'),
    ('carroceria', 'Carroceria', '🚗', 'Para-choques, faróis e retrovisores'),
]

PRODUCTS = [
    {
        'name': 'Pastilha de freio dianteira Gol G5/G6 1.0/1.6',
        'category': 'freios',
        'sku': 'SND-FRE-001',
        'oem_code': '6QD698151',
        'brand': 'TRW',
        'price': '89.90',
        'compare_at_price': '119.00',
        'stock': 24,
        'is_featured': True,
        'compatible_vehicles': 'VW Gol G5/G6 1.0/1.6 2008-2016',
        'description': 'Jogo dianteiro com alta durabilidade e baixo ruído. Material sem amianto.',
        'image_url': 'https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&h=450&fit=crop',
    },
    {
        'name': 'Disco de freio ventilado Corsa/Celta 256mm',
        'category': 'freios',
        'sku': 'SND-FRE-002',
        'oem_code': '93376652',
        'brand': 'Fremax',
        'price': '84.00',
        'stock': 18,
        'is_featured': True,
        'compatible_vehicles': 'Chevrolet Corsa, Celta, Prisma',
        'description': 'Disco ventilado sólido. Par dianteiro.',
        'image_url': 'https://images.unsplash.com/photo-1619642751034-765df036d329?w=600&h=450&fit=crop',
    },
    {
        'name': 'Amortecedor dianteiro Palio/Siena/Strada',
        'category': 'suspensao',
        'sku': 'SND-SUS-001',
        'oem_code': '51861429',
        'brand': 'Cofap',
        'price': '189.90',
        'compare_at_price': '229.00',
        'stock': 12,
        'is_featured': True,
        'compatible_vehicles': 'Fiat Palio, Siena, Strada 2004-2016',
        'description': 'Amortecedor a gás pressurizado. Unidade.',
        'image_url': 'https://images.unsplash.com/photo-1625047509248-ec889cbff124?w=600&h=450&fit=crop',
    },
    {
        'name': 'Pivô inferior Palio/Siena/Strada',
        'category': 'suspensao',
        'sku': 'SND-SUS-002',
        'oem_code': '46444638',
        'brand': 'Monroe',
        'price': '50.00',
        'stock': 30,
        'compatible_vehicles': 'Fiat Palio, Siena, Strada',
        'description': 'Pivô de suspensão com bucha reforçada.',
        'image_url': 'https://images.unsplash.com/photo-1492144534655-ae79c964c907?w=600&h=450&fit=crop',
    },
    {
        'name': 'Filtro de óleo VW/Audi 1.0 TSI',
        'category': 'filtros',
        'sku': 'SND-FIL-001',
        'oem_code': '04E115561H',
        'brand': 'Mann',
        'price': '32.90',
        'stock': 45,
        'is_featured': True,
        'compatible_vehicles': 'VW Up, Polo, Virtus 1.0 TSI',
        'description': 'Filtro de óleo original Mann Filter.',
        'image_url': 'https://images.unsplash.com/photo-1628177142898-93eaa6ab386?w=600&h=450&fit=crop',
    },
    {
        'name': 'Filtro de ar motor Honda Fit/City',
        'category': 'filtros',
        'sku': 'SND-FIL-002',
        'oem_code': '17220-R1A-A01',
        'brand': 'Tecfil',
        'price': '28.50',
        'stock': 38,
        'compatible_vehicles': 'Honda Fit/City 2015-2020',
        'description': 'Elemento filtrante de alta retenção de impurezas.',
        'image_url': 'https://images.unsplash.com/photo-1607860108858-0b93d5ca2567?w=600&h=450&fit=crop',
    },
    {
        'name': 'Bomba d\'água Ford Ka 1.0/1.5 Sigma',
        'category': 'motor',
        'sku': 'SND-MOT-001',
        'oem_code': '1S7Q8505AA',
        'brand': 'Indisa',
        'price': '145.00',
        'stock': 8,
        'is_featured': True,
        'compatible_vehicles': 'Ford Ka 1.0/1.5 2014-2021',
        'description': 'Bomba d\'água com junta. Sistema de arrefecimento.',
        'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&h=450&fit=crop',
    },
    {
        'name': 'Jogo de juntas motor Ranger 2.2 Duratorq',
        'category': 'motor',
        'sku': 'SND-MOT-002',
        'oem_code': 'AB3Q6051AA',
        'brand': 'Sabo',
        'price': '688.43',
        'stock': 3,
        'compatible_vehicles': 'Ford Ranger 2.2 2013-2020',
        'description': 'Kit completo de juntas do motor. Qualidade premium.',
        'image_url': 'https://images.unsplash.com/photo-1487754180451-c456f719a1fc?w=600&h=450&fit=crop',
    },
    {
        'name': 'Carcaça válvula termostática Ecosport 1.0/1.6',
        'category': 'motor',
        'sku': 'SND-MOT-003',
        'oem_code': '1S7G8594AA',
        'brand': 'Valeo',
        'price': '229.90',
        'stock': 6,
        'compatible_vehicles': 'Ford Ecosport 1.0/1.6 2005-2020',
        'description': 'Com sensor integrado. Sistema de arrefecimento.',
        'image_url': 'https://images.unsplash.com/photo-1615900126325-40d014aa0eab?w=600&h=450&fit=crop',
    },
    {
        'name': 'Alternador 90A Gol/Polo/Fox 1.0/1.6',
        'category': 'eletrica',
        'sku': 'SND-ELT-001',
        'oem_code': '037903023C',
        'brand': 'Bosch',
        'price': '389.00',
        'compare_at_price': '459.00',
        'stock': 5,
        'is_featured': True,
        'compatible_vehicles': 'VW Gol, Polo, Fox 1.0/1.6',
        'description': 'Alternador remanufaturado premium 90 amperes.',
        'image_url': 'https://images.unsplash.com/photo-1558618047-3c8c76ca7d13?w=600&h=450&fit=crop',
    },
    {
        'name': 'Bateria 60Ah livre de manutenção M18',
        'category': 'eletrica',
        'sku': 'SND-ELT-002',
        'oem_code': 'M18-60',
        'brand': 'Moura',
        'price': '459.00',
        'stock': 10,
        'compatible_vehicles': 'Veículos populares e médios',
        'description': 'Bateria selada 60Ah. Garantia de fábrica.',
        'image_url': 'https://images.unsplash.com/photo-1593941707882-a5bba14938ca?w=600&h=450&fit=crop',
    },
    {
        'name': 'Farol auxiliar milha universal LED',
        'category': 'carroceria',
        'sku': 'SND-CAR-001',
        'oem_code': 'LED-MILHA-01',
        'brand': 'Hella',
        'price': '159.90',
        'stock': 15,
        'compatible_vehicles': 'Universal — diversos modelos',
        'description': 'Par de faróis de milha LED 12V. Alta luminosidade.',
        'image_url': 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=600&h=450&fit=crop',
    },
    {
        'name': 'Retrovisor externo elétrico Uno/Palio lado direito',
        'category': 'carroceria',
        'sku': 'SND-CAR-002',
        'oem_code': '735422058',
        'brand': 'Importado',
        'price': '98.00',
        'stock': 7,
        'compatible_vehicles': 'Fiat Uno, Palio 2010-2016',
        'description': 'Retrovisor com regulagem elétrica. Lado passageiro.',
        'image_url': 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db?w=600&h=450&fit=crop',
    },
    {
        'name': 'Kit correia dentada Onix/Prisma 1.0/1.4',
        'category': 'motor',
        'sku': 'SND-MOT-004',
        'oem_code': '24586671',
        'brand': 'Gates',
        'price': '178.00',
        'stock': 11,
        'is_featured': True,
        'compatible_vehicles': 'Chevrolet Onix/Prisma 2012-2019',
        'description': 'Kit correia + tensor. Marca Gates original.',
        'image_url': 'https://images.unsplash.com/photo-1619642751034-765df036d329?w=600&h=450&fit=crop',
    },
    {
        'name': 'Fluido de freio DOT 4 500ml',
        'category': 'freios',
        'sku': 'SND-FRE-003',
        'oem_code': 'DOT4-500',
        'brand': 'Bosch',
        'price': '24.90',
        'stock': 60,
        'compatible_vehicles': 'Universal',
        'description': 'Fluido de freio sintético DOT 4. Alta ponto de ebulição.',
        'image_url': 'https://images.unsplash.com/photo-1628177142898-93eaa6ab386?w=600&h=450&fit=crop',
    },
]


class Command(BaseCommand):
    help = 'Cria categorias e peças demo da AutoPeças Sandroni'

    def handle(self, *args, **options):
        cats = {}
        for i, (slug, name, icon, desc) in enumerate(CATEGORIES):
            cat, _ = Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'description': desc, 'sort_order': i},
            )
            cats[slug] = cat
            self.stdout.write(f'Categoria: {cat.name}')

        created = 0
        for item in PRODUCTS:
            slug = slugify(item['name'])[:250]
            defaults = {
                'name': item['name'],
                'category': cats[item['category']],
                'sku': item['sku'],
                'oem_code': item.get('oem_code', ''),
                'brand': item.get('brand', ''),
                'price': Decimal(item['price']),
                'compare_at_price': Decimal(item['compare_at_price']) if item.get('compare_at_price') else None,
                'stock': item['stock'],
                'is_featured': item.get('is_featured', False),
                'is_active': True,
                'compatible_vehicles': item.get('compatible_vehicles', ''),
                'description': item.get('description', ''),
                'image_url': item.get('image_url', ''),
            }
            _, was_created = Product.objects.update_or_create(slug=slug, defaults=defaults)
            if was_created:
                created += 1
            self.stdout.write(f"  {'+' if was_created else '~'} {item['name']}")

        total = Product.objects.filter(is_active=True).count()
        config = SystemConfig.get_config()
        config.store_address = 'Rua São Sabino, 262'
        config.store_name = 'AutoPeças Sandroni'
        config.store_whatsapp = '11974452478'
        config.store_phone = '(11) 97445-2478'
        config.save(update_fields=['store_address', 'store_name', 'store_whatsapp', 'store_phone', 'updated_at'])
        self.stdout.write(self.style.SUCCESS(f'Pronto! {created} peças novas. Total ativo: {total}'))
