from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.text import slugify
from django.core.management.base import BaseCommand

from api.models import Product, Seller, SystemConfig

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria contas admin e Auto Peças Sandroni (vendedor ativo).'

    @transaction.atomic
    def handle(self, *args, **options):
        config = SystemConfig.get_config()

        admin, created_admin = User.objects.get_or_create(
            email='admin@admin.com',
            defaults={
                'name': 'Administrador',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        admin.set_password('admin')
        admin.is_active = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.name = 'Administrador'
        admin.save()
        self.stdout.write(self.style.SUCCESS(
            f"Admin: {'criado' if created_admin else 'atualizado'} — login admin / admin@admin.com · senha admin"
        ))

        sandroni_user, created_sandroni = User.objects.get_or_create(
            email='sandroni@sandroni.com',
            defaults={
                'name': 'Auto Peças Sandroni',
                'is_active': True,
                'phone': config.store_phone or '',
            },
        )
        sandroni_user.set_password('sandroni')
        sandroni_user.is_active = True
        sandroni_user.name = 'Auto Peças Sandroni'
        sandroni_user.save()
        self.stdout.write(self.style.SUCCESS(
            f"Sandroni: {'criado' if created_sandroni else 'atualizado'} — login sandroni / sandroni@sandroni.com · senha sandroni"
        ))

        slug = 'auto-pecas-sandroni'
        seller = Seller.objects.filter(user=sandroni_user).first()
        if not seller:
            seller = Seller.objects.filter(slug=slug).first()
        if seller:
            seller.user = sandroni_user
            seller.store_name = 'Auto Peças Sandroni'
            seller.slug = slug
            seller.status = Seller.Status.ACTIVE
            seller.is_official = True
            seller.ships_from_platform = False
            seller.origin_zip = config.origin_zip or seller.origin_zip or '01310100'
            seller.shipping_address = config.store_address or seller.shipping_address or 'Rua São Sabino, 262'
            seller.shipping_city = seller.shipping_city or 'São Paulo'
            seller.shipping_state = seller.shipping_state or 'SP'
            if not seller.estimated_stock_units:
                seller.estimated_stock_units = 500
            seller.save()
            created_seller = False
        else:
            seller = Seller.objects.create(
                user=sandroni_user,
                store_name='Auto Peças Sandroni',
                slug=slug,
                description='Loja oficial de autopeças — estoque físico na Rua São Sabino.',
                document='',
                phone=config.store_phone or config.store_whatsapp or '',
                status=Seller.Status.ACTIVE,
                is_official=True,
                ships_from_platform=False,
                origin_zip=config.origin_zip or '01310100',
                shipping_address=config.store_address or 'Rua São Sabino, 262',
                shipping_city='São Paulo',
                shipping_state='SP',
                estimated_stock_units=500,
            )
            created_seller = True

        Seller.objects.filter(is_official=True).exclude(pk=seller.pk).update(is_official=False)

        linked = Product.objects.filter(seller__isnull=True).update(seller=seller)
        config.store_name = 'Auto Peças Sandroni'
        config.save(update_fields=['store_name', 'updated_at'])

        self.stdout.write(self.style.SUCCESS(
            f"Loja vendedora: {seller.store_name} (ativa, oficial) — {linked} peça(s) vinculada(s)"
        ))
        self.stdout.write('Painel admin: /painel/entrar/ · e-mail admin@admin.com · senha admin')
        self.stdout.write('Vender peças: /vender/ · login sandroni · senha sandroni')
