# Generated manually for slug field

from django.db import migrations, models


def set_default_slugs(apps, schema_editor):
    """Define slug baseado no id para pedidos existentes"""
    Order = apps.get_model('api', 'Order')
    for order in Order.objects.all():
        if not order.slug:
            order.slug = f'pedido-{order.id}'
            order.save()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_add_order_email_verification_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='slug',
            field=models.SlugField(blank=True, db_index=True, max_length=80, null=True, unique=True, verbose_name='Nome do link (ex: joao-e-maria)'),
        ),
        migrations.RunPython(set_default_slugs, migrations.RunPython.noop),
    ]
