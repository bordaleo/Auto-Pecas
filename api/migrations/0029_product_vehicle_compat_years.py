from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0028_part_request_enhancements'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='productvehiclecompatibility',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='productvehiclecompatibility',
            name='year_start',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Vazio = todos os anos do modelo FIPE.',
                null=True,
                verbose_name='Ano início compat.',
            ),
        ),
        migrations.AddField(
            model_name='productvehiclecompatibility',
            name='year_end',
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text='Vazio = todos os anos do modelo FIPE.',
                null=True,
                verbose_name='Ano fim compat.',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='productvehiclecompatibility',
            unique_together={('product', 'vehicle_model', 'year_start', 'year_end')},
        ),
    ]
