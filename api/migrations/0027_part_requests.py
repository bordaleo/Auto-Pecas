from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0026_seller_application'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField(verbose_name='Descrição da peça')),
                ('vehicle_brand', models.CharField(blank=True, default='', max_length=80, verbose_name='Marca do veículo')),
                ('vehicle_model', models.CharField(blank=True, default='', max_length=120, verbose_name='Modelo do veículo')),
                ('vehicle_year', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Ano do veículo')),
                ('contact_phone', models.CharField(blank=True, default='', max_length=20, verbose_name='Telefone para contato')),
                ('show_phone', models.BooleanField(default=True, verbose_name='Exibir telefone aos vendedores')),
                ('status', models.CharField(
                    choices=[('open', 'Aberta'), ('closed', 'Encerrada'), ('fulfilled', 'Atendida')],
                    db_index=True, default='open', max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='Encerrada em')),
                ('requester', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='part_requests', to='api.user', verbose_name='Solicitante',
                )),
            ],
            options={
                'verbose_name': 'Pedido de peça',
                'verbose_name_plural': 'Pedidos de peça',
                'db_table': 'part_requests',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PartRequestConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_message_at', models.DateTimeField(auto_now_add=True, verbose_name='Última mensagem')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('buyer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='part_request_conversations', to='api.user', verbose_name='Solicitante',
                )),
                ('part_request', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='conversations', to='api.partrequest', verbose_name='Pedido',
                )),
                ('seller', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='part_request_conversations', to='api.seller', verbose_name='Vendedor',
                )),
            ],
            options={
                'verbose_name': 'Conversa sobre pedido de peça',
                'verbose_name_plural': 'Conversas sobre pedidos de peça',
                'db_table': 'part_request_conversations',
                'ordering': ['-last_message_at'],
                'unique_together': {('part_request', 'seller')},
            },
        ),
        migrations.CreateModel(
            name='PartRequestMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField(verbose_name='Mensagem')),
                ('is_read', models.BooleanField(default=False, verbose_name='Lida')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Enviada em')),
                ('conversation', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages', to='api.partrequestconversation', verbose_name='Conversa',
                )),
                ('sender', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='part_request_messages', to='api.user', verbose_name='Remetente',
                )),
            ],
            options={
                'verbose_name': 'Mensagem (pedido de peça)',
                'verbose_name_plural': 'Mensagens (pedido de peça)',
                'db_table': 'part_request_messages',
                'ordering': ['created_at'],
            },
        ),
    ]
