# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0029_product_vehicle_compat_years'),
    ]

    operations = [
        migrations.CreateModel(
            name='CatalogSearchEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(
                    choices=[
                        ('search', 'Busca'),
                        ('popular_click', 'Clique em termo popular'),
                        ('purchase', 'Compra'),
                    ],
                    db_index=True,
                    max_length=20,
                )),
                ('term', models.CharField(blank=True, db_index=True, default='', max_length=200)),
                ('session_key', models.CharField(blank=True, db_index=True, default='', max_length=64)),
                ('filters', models.JSONField(blank=True, default=dict)),
                ('result_count', models.PositiveIntegerField(blank=True, null=True)),
                ('source', models.CharField(blank=True, default='', max_length=40)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('product', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='search_purchases',
                    to='api.product',
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='catalog_searches',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'catalog_search_events',
            },
        ),
        migrations.AddIndex(
            model_name='catalogsearchevent',
            index=models.Index(fields=['term', '-created_at'], name='catalog_se_term_created_idx'),
        ),
        migrations.AddIndex(
            model_name='catalogsearchevent',
            index=models.Index(fields=['event_type', '-created_at'], name='catalog_se_type_created_idx'),
        ),
    ]
