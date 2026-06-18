from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0017_sandroni_shop'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_method',
            field=models.CharField(
                choices=[('delivery', 'Entrega'), ('pickup', 'Retirada na loja')],
                default='delivery',
                max_length=20,
                verbose_name='Forma de recebimento',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_fee',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
                verbose_name='Valor do frete',
            ),
        ),
        migrations.AlterField(
            model_name='systemconfig',
            name='store_address',
            field=models.CharField(
                blank=True,
                default='Rua São Sabino, 262',
                max_length=255,
                verbose_name='Endereço',
            ),
        ),
    ]
