from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0025_seller_shipping'),
    ]

    operations = [
        migrations.AddField(
            model_name='seller',
            name='estimated_stock_units',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Quantidade aproximada de peças que o vendedor informou na solicitação.',
                verbose_name='Peças em estoque (aprox.)',
            ),
        ),
        migrations.AddField(
            model_name='seller',
            name='admin_notes',
            field=models.TextField(blank=True, default='', verbose_name='Notas do admin'),
        ),
        migrations.AlterField(
            model_name='seller',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Aguardando aprovação'),
                    ('active', 'Ativa'),
                    ('suspended', 'Suspensa'),
                    ('rejected', 'Rejeitada'),
                ],
                db_index=True,
                default='pending',
                max_length=20,
                verbose_name='Status',
            ),
        ),
    ]
