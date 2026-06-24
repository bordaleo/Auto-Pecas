"""Respostas simuladas da Nuvem Fiscal (desenvolvimento sem certificado/API real)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings

MOCK_PDF_BYTES = (
    b'%PDF-1.4\n'
    b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
    b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
    b'3 0 obj<</Type/Page/MediaBox[0 0 400 200]/Parent 2 0 R/Contents 4 0 R>>endobj\n'
    b'4 0 obj<</Length 68>>stream\n'
    b'BT /F1 14 Tf 40 120 Td (NF-e SIMULADA - Galelugi Pecas) Tj ET\n'
    b'endstream\nendobj\n'
    b'xref\n0 5\n0000000000 65535 f \n'
    b'trailer<</Size 5/Root 1 0 R>>\n'
    b'startxref\n300\n%%EOF'
)


def mock_nfe_id(invoice_request_id: int) -> str:
    return f'mock-nfe-{invoice_request_id}'


def mock_nfe_chave(invoice_request_id: int, order_id: int) -> str:
    """Chave fictícia de 44 dígitos (apenas para UI/testes)."""
    raw = f'35{order_id:011d}{invoice_request_id:011d}'
    return raw[:44].ljust(44, '0')


def mock_dfe(invoice_request, *, status: str = 'autorizado') -> dict:
    now = datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat()
    numero = 100000 + int(invoice_request.id)
    chave = mock_nfe_chave(invoice_request.id, invoice_request.order_id)
    return {
        'id': mock_nfe_id(invoice_request.id),
        'ambiente': 'homologacao',
        'status': status,
        'referencia': f'galelugi-inv-{invoice_request.id}',
        'created_at': now,
        'modelo': 55,
        'serie': 1,
        'numero': numero,
        'valor_total': float(invoice_request.order.amount or 0),
        'chave': chave,
        'mock': True,
        'autorizacao': {
            'status': '100',
            'motivo_status': 'Autorizado o uso da NF-e (simulado)',
            'protocolo': f'MOCK{invoice_request.id:08d}',
        },
    }


def apply_mock_emission(invoice_request) -> dict:
    """Marca solicitação como emitida com dados fictícios."""
    dfe = mock_dfe(invoice_request)
    invoice_request.nuvem_fiscal_id = dfe['id']
    invoice_request.nuvem_fiscal_status = 'autorizado'
    invoice_request.nuvem_fiscal_chave = dfe['chave']
    invoice_request.invoice_number = str(dfe['numero'])
    invoice_request.status = 'issued'
    backend = getattr(settings, 'BACKEND_URL', 'http://127.0.0.1:8000').rstrip('/')
    invoice_request.invoice_url = f'{backend}/api/v1/invoices/{invoice_request.id}/nfe-pdf/'
    note = 'NF-e emitida em modo simulado (NUVEM_FISCAL_MOCK=true). Sem valor fiscal.'
    if note not in (invoice_request.admin_notes or ''):
        invoice_request.admin_notes = f'{note}\n{invoice_request.admin_notes}'.strip()[:2000]
    invoice_request.save()
    return dfe


def consult_mock_nfe(dfe_id: str) -> dict:
    if not dfe_id.startswith('mock-nfe-'):
        return {'id': dfe_id, 'status': 'autorizado', 'mock': True}
    inv_id = int(dfe_id.replace('mock-nfe-', '') or '0')
    numero = 100000 + inv_id
    chave = mock_nfe_chave(inv_id, inv_id)
    return {
        'id': dfe_id,
        'status': 'autorizado',
        'numero': numero,
        'chave': chave,
        'mock': True,
    }


def mock_lookup_cep(cep_digits: str) -> dict:
    return {
        'cep': cep_digits,
        'codigo_ibge': '3550308',
        'municipio': 'Sao Paulo',
        'uf': 'SP',
        'mock': True,
    }
