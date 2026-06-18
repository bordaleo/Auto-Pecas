#!/usr/bin/env python
"""
Script de teste para verificar a configuração do Mercado Pago
Execute: python test_mp.py
"""

import os
import sys
import django

# Configura Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"[ERRO] Erro ao configurar Django: {e}")
    sys.exit(1)

from api.services.payment_service import payment_service
from django.conf import settings
import logging

# Configura logging para ver mensagens
logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("TESTE DE CONFIGURAÇÃO DO MERCADO PAGO")
print("=" * 60)
print()

# Verifica configuração
print("1. Verificando configuração...")
print(f"   MERCADOPAGO_ACCESS_TOKEN no settings: {bool(getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', None))}")
print(f"   Token configurado: {bool(payment_service.access_token)}")
print(f"   Serviço habilitado: {payment_service.enabled}")

if payment_service.access_token:
    token_preview = payment_service.access_token[:20] + "..." if len(payment_service.access_token) > 20 else payment_service.access_token
    print(f"   Token (preview): {token_preview}")
    print(f"   Token começa com TEST?: {'SIM [OK]' if payment_service.access_token.startswith('TEST-') else 'NAO [AVISO]'}")
else:
    print("   ❌ Token não encontrado! Verifique o arquivo .env")
    sys.exit(1)

print()

if not payment_service.enabled:
    print("[ERRO] Servico nao esta habilitado!")
    sys.exit(1)

# Testa criação de preferência
print("2. Testando criação de preferência...")
print("   Criando preferência de teste...")
print()

try:
    result = payment_service.create_payment_preference(
        plan="lifetime",
        amount=29.99,
        user_id=1,
        user_name="Teste User",
        user_email="test@test.com",
        external_reference="test_123"
    )
    
    if result:
        preference_id = result.get('id')
        init_point = result.get('init_point', 'N/A')
        sandbox_init_point = result.get('sandbox_init_point', 'N/A')
        
        print("[SUCESSO] Preferencia criada com sucesso!")
        print()
        print(f"   Preference ID: {preference_id}")
        print(f"   Init Point: {init_point[:50]}..." if len(init_point) > 50 else f"   Init Point: {init_point}")
        print(f"   Sandbox Init Point: {sandbox_init_point[:50]}..." if len(sandbox_init_point) > 50 else f"   Sandbox Init Point: {sandbox_init_point}")
        print()
        print("=" * 60)
        print("[OK] TUDO OK! O Mercado Pago esta configurado corretamente.")
        print("=" * 60)
    else:
        print("[ERRO] Falha ao criar preferencia!")
        print("   O metodo retornou None. Verifique os logs acima para mais detalhes.")
        sys.exit(1)
        
except Exception as e:
    print(f"[ERRO] ERRO ao criar preferencia: {e}")
    print()
    import traceback
    print("Detalhes do erro:")
    traceback.print_exc()
    sys.exit(1)
