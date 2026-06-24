from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify
from django.core.management.base import BaseCommand

from api.models import Seller, SystemConfig

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria ou atualiza a loja oficial Auto Peças Sandroni (vendedor com selo oficial).'

    def add_arguments(self, parser):
        parser.add_argument('--email', help='E-mail do usuário admin (padrão: primeiro superuser)')
        parser.add_argument('--store-name', default='Auto Peças Sandroni', help='Nome da loja')
        parser.add_argument('--origin-zip', default='', help='CEP de origem (padrão: origin_zip do SystemConfig)')
        parser.add_argument('--activate', action='store_true', help='Ativa a loja imediatamente')

    @transaction.atomic
    def handle(self, *args, **options):
        config = SystemConfig.get_config()
        store_name = options['store_name'].strip()
        origin_zip = (options['origin_zip'] or config.origin_zip or '01310100').replace('-', '').strip()[:8]

        email = options.get('email')
        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        if not user:
            user = User.objects.filter(is_superuser=True).order_by('id').first()
        if not user:
            self.stderr.write(self.style.ERROR('Nenhum usuário encontrado. Use --email.'))
            return

        slug = slugify(store_name)[:100] or 'auto-pecas-sandroni'
        seller = Seller.objects.filter(user=user).first()
        if not seller:
            base_slug = slug
            counter = 1
            while Seller.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            seller = Seller.objects.create(
                user=user,
                store_name=store_name,
                slug=slug,
                description='Loja oficial Galelugi — peças automotivas com envio e retirada na Sandroni.',
                status=Seller.Status.ACTIVE,
                is_official=True,
                ships_from_platform=False,
                origin_zip=origin_zip,
                shipping_address=config.store_address or 'Rua São Sabino, 262',
                shipping_city='São Paulo',
                shipping_state='SP',
            )
            created = True
        else:
            created = False
            seller.store_name = store_name
            seller.is_official = True
            seller.ships_from_platform = False
            seller.origin_zip = origin_zip or seller.origin_zip
            if options.get('activate'):
                seller.status = Seller.Status.ACTIVE
            seller.save()

        Seller.objects.filter(is_official=True).exclude(pk=seller.pk).update(is_official=False)

        if config.store_name != store_name:
            config.store_name = store_name
            config.save(update_fields=['store_name', 'updated_at'])

        verb = 'Criada' if created else 'Atualizada'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} loja oficial: {seller.store_name} (slug: {seller.slug}, user: {user.email})'
        ))
        self.stdout.write(f'CEP origem frete: {seller.origin_zip}')
        self.stdout.write('Atribua produtos a este vendedor ou deixe seller=null para estoque da plataforma.')
