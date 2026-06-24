from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0023_growth_platform'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicerequest',
            name='nuvem_fiscal_chave',
            field=models.CharField(blank=True, default='', max_length=44, verbose_name='Chave NF-e'),
        ),
        migrations.AddField(
            model_name='invoicerequest',
            name='nuvem_fiscal_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64, verbose_name='ID Nuvem Fiscal'),
        ),
        migrations.AddField(
            model_name='invoicerequest',
            name='nuvem_fiscal_status',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='Status Nuvem Fiscal'),
        ),
    ]
