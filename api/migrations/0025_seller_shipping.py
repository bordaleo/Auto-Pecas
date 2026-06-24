from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_invoice_nuvem_fiscal'),
    ]

    operations = [
        migrations.AddField(
            model_name='seller',
            name='origin_zip',
            field=models.CharField(blank=True, default='', max_length=12, verbose_name='CEP de origem (frete)'),
        ),
        migrations.AddField(
            model_name='seller',
            name='shipping_address',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='Endereço de envio'),
        ),
        migrations.AddField(
            model_name='seller',
            name='shipping_city',
            field=models.CharField(blank=True, default='', max_length=120, verbose_name='Cidade'),
        ),
        migrations.AddField(
            model_name='seller',
            name='shipping_state',
            field=models.CharField(blank=True, default='', max_length=2, verbose_name='UF'),
        ),
        migrations.AddField(
            model_name='seller',
            name='ships_from_platform',
            field=models.BooleanField(
                default=False,
                help_text='Peças saem do endereço da loja oficial, não do CEP do vendedor.',
                verbose_name='Envio pela plataforma (Sandroni)',
            ),
        ),
        migrations.AddField(
            model_name='seller',
            name='is_official',
            field=models.BooleanField(
                default=False,
                help_text='Exibe selo de loja oficial (ex.: Auto Peças Sandroni).',
                verbose_name='Loja oficial',
            ),
        ),
    ]
