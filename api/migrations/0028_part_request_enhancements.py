from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


def set_commission_to_8(apps, schema_editor):
    SystemConfig = apps.get_model('api', 'SystemConfig')
    SystemConfig.objects.filter(marketplace_commission_percent=Decimal('12.00')).update(
        marketplace_commission_percent=Decimal('8.00'),
    )
    SystemConfig.objects.filter(marketplace_commission_percent__gt=Decimal('8.00')).update(
        marketplace_commission_percent=Decimal('8.00'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0027_part_requests'),
    ]

    operations = [
        migrations.AddField(
            model_name='partrequest',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Expira em'),
        ),
        migrations.AddField(
            model_name='partrequest',
            name='plate',
            field=models.CharField(blank=True, default='', max_length=12, verbose_name='Placa'),
        ),
        migrations.AddField(
            model_name='partrequest',
            name='requester_zip',
            field=models.CharField(blank=True, default='', max_length=12, verbose_name='CEP solicitante'),
        ),
        migrations.AddField(
            model_name='partrequest',
            name='vin',
            field=models.CharField(blank=True, default='', max_length=17, verbose_name='VIN'),
        ),
        migrations.AddField(
            model_name='partrequest',
            name='vehicle_model_ref',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='part_requests', to='api.vehiclemodel',
                verbose_name='Modelo veicular (catálogo)',
            ),
        ),
        migrations.AddField(
            model_name='partrequestconversation',
            name='quote_condition',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Condição orçada'),
        ),
        migrations.AddField(
            model_name='partrequestconversation',
            name='quote_delivery_days',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Prazo entrega (dias úteis)'),
        ),
        migrations.AddField(
            model_name='partrequestconversation',
            name='quote_notes',
            field=models.TextField(blank=True, default='', verbose_name='Observações do orçamento'),
        ),
        migrations.AddField(
            model_name='partrequestconversation',
            name='quote_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Preço orçado'),
        ),
        migrations.AddField(
            model_name='partrequestconversation',
            name='quote_product',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='part_request_quotes', to='api.product', verbose_name='Peça vinculada',
            ),
        ),
        migrations.CreateModel(
            name='PartRequestRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(verbose_name='Nota (1-5)')),
                ('comment', models.TextField(blank=True, default='', verbose_name='Comentário')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Avaliado em')),
                ('conversation', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='rating', to='api.partrequestconversation', verbose_name='Conversa',
                )),
            ],
            options={
                'verbose_name': 'Avaliação de pedido de peça',
                'verbose_name_plural': 'Avaliações de pedidos de peça',
                'db_table': 'part_request_ratings',
            },
        ),
        migrations.AlterField(
            model_name='systemconfig',
            name='marketplace_commission_percent',
            field=models.DecimalField(
                decimal_places=2, default=Decimal('8.00'), help_text='Percentual retido pela Galelugi em cada venda de vendedor',
                max_digits=5, verbose_name='Comissão do marketplace (%)',
            ),
        ),
        migrations.RunPython(set_commission_to_8, migrations.RunPython.noop),
    ]
