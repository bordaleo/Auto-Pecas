# Generated manually for marketplace

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_order_shipping'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemconfig',
            name='marketplace_commission_percent',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('12.00'),
                help_text='Percentual retido pela Galelugi em cada venda de vendedor',
                max_digits=5,
                verbose_name='Comissão do marketplace (%)',
            ),
        ),
        migrations.CreateModel(
            name='Seller',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_name', models.CharField(max_length=120, verbose_name='Nome da loja')),
                ('slug', models.SlugField(max_length=120, unique=True, verbose_name='Slug')),
                ('description', models.TextField(blank=True, default='', verbose_name='Descrição')),
                ('document', models.CharField(blank=True, default='', max_length=20, verbose_name='CPF/CNPJ')),
                ('phone', models.CharField(blank=True, default='', max_length=20, verbose_name='Telefone')),
                ('status', models.CharField(
                    choices=[('pending', 'Aguardando aprovação'), ('active', 'Ativa'), ('suspended', 'Suspensa')],
                    db_index=True,
                    default='pending',
                    max_length=20,
                    verbose_name='Status',
                )),
                ('commission_rate', models.DecimalField(
                    blank=True,
                    decimal_places=2,
                    help_text='Vazio = usa taxa padrão da plataforma',
                    max_digits=5,
                    null=True,
                    verbose_name='Comissão personalizada (%)',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='seller_profile',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Usuário',
                )),
            ],
            options={
                'verbose_name': 'Vendedor',
                'verbose_name_plural': 'Vendedores',
                'db_table': 'sellers',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='product',
            name='seller',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products',
                to='api.seller',
                verbose_name='Vendedor',
            ),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='seller',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='order_items',
                to='api.seller',
                verbose_name='Vendedor',
            ),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='platform_fee',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='Comissão Galelugi'),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='seller_earning',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='Repasse ao vendedor'),
        ),
    ]
