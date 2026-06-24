"""Fluxo de solicitação e emissão de NF-e."""

from django.conf import settings

from api.models import InvoiceRequest, InvoiceStatus
from api.services.email_service import email_service
from api.services.notification_service import notify_invoice_issued, notify_seller_invoice_requested
from api.services.nuvem_fiscal_service import NuvemFiscalError, emit_invoice_nfe, is_configured
from api.utils import normalize_cnpj, validate_cnpj


def validate_invoice_create_payload(*, cnpj: str, company_name: str):
    cnpj_digits = normalize_cnpj(cnpj)
    if len(cnpj_digits) != 14:
        return None, 'Informe um CNPJ válido com 14 dígitos.'
    if not validate_cnpj(cnpj_digits):
        return None, 'CNPJ inválido. Verifique os números informados.'
    company_name = (company_name or '').strip()
    if len(company_name) < 3:
        return None, 'Razão social é obrigatória.'
    return {
        'cnpj': cnpj_digits,
        'company_name': company_name,
    }, None


def on_invoice_requested(invoice_request: InvoiceRequest):
    notify_seller_invoice_requested(invoice_request)
    seller = invoice_request.seller
    if seller and seller.user_id:
        email_service.send_invoice_requested_email(invoice_request)


def apply_invoice_update(invoice_request: InvoiceRequest, data: dict) -> str | None:
    """Atualiza solicitação. Retorna mensagem de erro ou None se ok."""
    previous_status = invoice_request.status
    new_status = data.get('status')
    if new_status in dict(InvoiceStatus.choices):
        invoice_request.status = new_status

    if 'invoice_number' in data:
        invoice_request.invoice_number = (data.get('invoice_number') or '').strip()
    if 'invoice_url' in data:
        invoice_request.invoice_url = (data.get('invoice_url') or '').strip()
    if 'admin_notes' in data:
        invoice_request.admin_notes = (data.get('admin_notes') or '').strip()

    if invoice_request.status == InvoiceStatus.ISSUED:
        if not invoice_request.invoice_number:
            return 'Informe o número da NF-e antes de marcar como emitida.'
        if not invoice_request.invoice_url and not invoice_request.nuvem_fiscal_id:
            return 'Informe a URL do PDF/XML antes de marcar como emitida.'

    invoice_request.save()

    if invoice_request.status == InvoiceStatus.ISSUED and previous_status != InvoiceStatus.ISSUED:
        notify_invoice_issued(invoice_request.user, invoice_request)
        email_service.send_invoice_issued_email(invoice_request)

    return None


def emit_invoice_via_nuvem_fiscal(invoice_request: InvoiceRequest) -> dict:
    """Emite NF-e automaticamente via Nuvem Fiscal."""
    if not is_configured():
        raise NuvemFiscalError(
            'Integração Nuvem Fiscal não configurada. '
            'Defina NUVEM_FISCAL_MOCK=true ou as credenciais da API.',
        )
    if invoice_request.status == InvoiceStatus.ISSUED and invoice_request.nuvem_fiscal_status == 'autorizado':
        return {'already_issued': True, 'id': invoice_request.nuvem_fiscal_id}

    previous_status = invoice_request.status
    invoice_request.status = InvoiceStatus.PROCESSING
    invoice_request.save(update_fields=['status', 'updated_at'])

    try:
        dfe = emit_invoice_nfe(invoice_request)
    except NuvemFiscalError:
        invoice_request.refresh_from_db()
        if invoice_request.status != InvoiceStatus.ISSUED:
            invoice_request.status = InvoiceStatus.PROCESSING
            invoice_request.save(update_fields=['status', 'updated_at'])
        raise

    if invoice_request.status == InvoiceStatus.ISSUED and previous_status != InvoiceStatus.ISSUED:
        notify_invoice_issued(invoice_request.user, invoice_request)
        email_service.send_invoice_issued_email(invoice_request)

    return dfe
