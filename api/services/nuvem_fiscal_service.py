"""Cliente da API Nuvem Fiscal (OAuth2 + NF-e)."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache

from api.utils import normalize_cnpj
from config.secrets import cfg, cfg_bool

logger = logging.getLogger(__name__)

AUTH_URL = 'https://auth.nuvemfiscal.com.br/oauth/token'
API_PRODUCTION = 'https://api.nuvemfiscal.com.br'
API_SANDBOX = 'https://api.sandbox.nuvemfiscal.com.br'
TOKEN_CACHE_KEY = 'nuvem_fiscal_access_token'

UF_IBGE = {
    'AC': 12, 'AL': 27, 'AM': 13, 'AP': 16, 'BA': 29, 'CE': 23, 'DF': 53, 'ES': 32,
    'GO': 52, 'MA': 21, 'MG': 31, 'MS': 50, 'MT': 51, 'PA': 15, 'PB': 25, 'PE': 26,
    'PI': 22, 'PR': 41, 'RJ': 33, 'RN': 24, 'RO': 11, 'RR': 14, 'RS': 43, 'SC': 42,
    'SE': 28, 'SP': 35, 'TO': 17,
}

HOMOLOG_DEST_NAME = 'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL'


class NuvemFiscalError(Exception):
    def __init__(self, message: str, *, code: str = '', status: int = 0, payload=None):
        super().__init__(message)
        self.code = code
        self.status = status
        self.payload = payload or {}


@dataclass
class NuvemFiscalConfig:
    client_id: str
    client_secret: str
    sandbox: bool
    emitter_document: str  # CPF (11) ou CNPJ (14)
    emitter_uf: str
    emitter_city_ibge: str
    default_ncm: str
    crt: int
    cfop: str
    scope: str

    @property
    def emitter_cnpj(self) -> str:
        """Compatibilidade — retorna documento se for CNPJ."""
        return self.emitter_document if len(self.emitter_document) == 14 else ''

    @property
    def emitter_is_cpf(self) -> bool:
        return len(self.emitter_document) == 11

    @property
    def api_base(self) -> str:
        return API_SANDBOX if self.sandbox else API_PRODUCTION

    @property
    def ambiente(self) -> str:
        return 'homologacao' if self.sandbox else 'producao'

    @property
    def tp_amb(self) -> int:
        return 2 if self.sandbox else 1


def _resolve_emitter_document_from_settings() -> str:
    cnpj = normalize_cnpj(cfg('NUVEM_FISCAL_EMITTER_CNPJ', ''))
    if len(cnpj) == 14:
        return cnpj
    cpf = normalize_cnpj(cfg('NUVEM_FISCAL_EMITTER_CPF', ''))
    if len(cpf) == 11:
        return cpf
    return ''


def _emit_identification(document: str) -> dict:
    if len(document) == 14:
        return {'CNPJ': document}
    if len(document) == 11:
        return {'CPF': document}
    raise NuvemFiscalError('Documento do emitente inválido (use CPF 11 ou CNPJ 14 dígitos).')


def is_mock_mode() -> bool:
    return cfg_bool('NUVEM_FISCAL_MOCK', False)


def get_config() -> NuvemFiscalConfig | None:
    if is_mock_mode():
        emitter_document = _resolve_emitter_document_from_settings() or '50556679822'
        return NuvemFiscalConfig(
            client_id='mock',
            client_secret='mock',
            sandbox=True,
            emitter_document=emitter_document,
            emitter_uf=(cfg('NUVEM_FISCAL_EMITTER_UF', 'SP') or 'SP').strip().upper()[:2],
            emitter_city_ibge=(cfg('NUVEM_FISCAL_EMITTER_CITY_IBGE', '3550308') or '3550308').strip(),
            default_ncm=(cfg('NUVEM_FISCAL_DEFAULT_NCM', '87089990') or '87089990').strip(),
            crt=int(cfg('NUVEM_FISCAL_CRT', '1') or '1'),
            cfop=(cfg('NUVEM_FISCAL_CFOP', '5102') or '5102').strip(),
            scope='mock',
        )

    client_id = (cfg('NUVEM_FISCAL_CLIENT_ID', '') or '').strip()
    client_secret = (cfg('NUVEM_FISCAL_CLIENT_SECRET', '') or '').strip()
    if not client_id or not client_secret:
        return None
    emitter_document = _resolve_emitter_document_from_settings()
    if len(emitter_document) not in (11, 14):
        return None
    return NuvemFiscalConfig(
        client_id=client_id,
        client_secret=client_secret,
        sandbox=cfg_bool('NUVEM_FISCAL_SANDBOX', True),
        emitter_document=emitter_document,
        emitter_uf=(cfg('NUVEM_FISCAL_EMITTER_UF', 'SP') or 'SP').strip().upper()[:2],
        emitter_city_ibge=(cfg('NUVEM_FISCAL_EMITTER_CITY_IBGE', '3550308') or '3550308').strip(),
        default_ncm=(cfg('NUVEM_FISCAL_DEFAULT_NCM', '87089990') or '87089990').strip(),
        crt=int(cfg('NUVEM_FISCAL_CRT', '1') or '1'),
        cfop=(cfg('NUVEM_FISCAL_CFOP', '5102') or '5102').strip(),
        scope=(cfg('NUVEM_FISCAL_SCOPE', 'nfe cep empresa') or 'nfe cep empresa').strip(),
    )


def is_configured() -> bool:
    return is_mock_mode() or get_config() is not None


def _http_request(
    method: str,
    url: str,
    *,
    headers: dict | None = None,
    data: bytes | None = None,
    timeout: int = 60,
) -> tuple[int, dict | bytes]:
    req = urllib.request.Request(url, data=data, method=method.upper())
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            content_type = resp.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                return resp.status, json.loads(body.decode('utf-8') or '{}')
            return resp.status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode('utf-8', errors='replace')
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {'detail': raw}
        message = payload.get('error', {}).get('message') if isinstance(payload.get('error'), dict) else None
        if not message:
            message = payload.get('detail') or payload.get('message') or raw or exc.reason
        code = ''
        if isinstance(payload.get('error'), dict):
            code = payload['error'].get('code', '')
        raise NuvemFiscalError(str(message), code=code, status=exc.code, payload=payload) from exc


def get_access_token(*, force_refresh: bool = False) -> str:
    if is_mock_mode():
        return 'mock-access-token-galelugi'

    config = get_config()
    if not config:
        raise NuvemFiscalError(
            'Nuvem Fiscal não configurada. Defina NUVEM_FISCAL_CLIENT_ID, '
            'NUVEM_FISCAL_CLIENT_SECRET e NUVEM_FISCAL_EMITTER_CPF ou NUVEM_FISCAL_EMITTER_CNPJ.',
        )
    if not force_refresh:
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

    body = urllib.parse.urlencode({
        'grant_type': 'client_credentials',
        'client_id': config.client_id,
        'client_secret': config.client_secret,
        'scope': config.scope,
    }).encode('utf-8')
    _, payload = _http_request(
        'POST',
        AUTH_URL,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=body,
        timeout=30,
    )
    token = payload.get('access_token')
    if not token:
        raise NuvemFiscalError('Token OAuth não retornado pela Nuvem Fiscal.')
    expires_in = int(payload.get('expires_in', 3600))
    cache.set(TOKEN_CACHE_KEY, token, max(expires_in - 120, 60))
    return token


def api_request(method: str, path: str, *, json_body: dict | None = None, params: dict | None = None):
    if is_mock_mode():
        raise NuvemFiscalError('Chamada HTTP bloqueada: NUVEM_FISCAL_MOCK está ativo.')

    config = get_config()
    if not config:
        raise NuvemFiscalError('Nuvem Fiscal não configurada.')
    query = f'?{urllib.parse.urlencode(params)}' if params else ''
    url = f'{config.api_base}{path}{query}'
    headers = {
        'Authorization': f'Bearer {get_access_token()}',
        'Accept': 'application/json',
    }
    data = None
    if json_body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(json_body).encode('utf-8')
    status, payload = _http_request(method, url, headers=headers, data=data)
    return status, payload


def api_request_bytes(method: str, path: str, *, params: dict | None = None) -> bytes:
    if is_mock_mode():
        from api.services.nuvem_fiscal_mock import MOCK_PDF_BYTES
        return MOCK_PDF_BYTES

    config = get_config()
    if not config:
        raise NuvemFiscalError('Nuvem Fiscal não configurada.')
    query = f'?{urllib.parse.urlencode(params)}' if params else ''
    url = f'{config.api_base}{path}{query}'
    headers = {'Authorization': f'Bearer {get_access_token()}', 'Accept': 'application/pdf'}
    _, payload = _http_request('GET', url, headers=headers)
    if isinstance(payload, bytes):
        return payload
    raise NuvemFiscalError('Resposta inesperada ao baixar PDF da NF-e.')


def lookup_cep(cep: str) -> dict:
    digits = normalize_cnpj(cep)[:8]
    if len(digits) != 8:
        return {}
    if is_mock_mode():
        from api.services.nuvem_fiscal_mock import mock_lookup_cep
        return mock_lookup_cep(digits)
    _, payload = api_request('GET', f'/cep/{digits}')
    return payload if isinstance(payload, dict) else {}


def sefaz_status(cnpj: str | None = None) -> dict:
    if is_mock_mode():
        config = get_config()
        doc = normalize_cnpj(cnpj or (config.emitter_document if config else ''))
        return {
            'mock': True,
            'cpf_cnpj': doc,
            'status': 'online',
            'mensagem': 'SEFAZ simulada — modo mock ativo',
        }

    config = get_config()
    if not config:
        raise NuvemFiscalError('Nuvem Fiscal não configurada.')
    doc = normalize_cnpj(cnpj or config.emitter_document)
    _, payload = api_request('GET', '/nfe/sefaz/status', params={
        'cpf_cnpj': doc,
        'autorizador': config.emitter_uf,
    })
    return payload


def upload_empresa_certificado(
    pfx_path: str,
    password: str,
    *,
    cpf_cnpj: str | None = None,
) -> dict:
    """Envia certificado A1 (.pfx) para a empresa na Nuvem Fiscal."""
    if is_mock_mode():
        return {
            'mock': True,
            'message': 'Upload de certificado simulado (NUVEM_FISCAL_MOCK=true).',
        }

    import base64
    from pathlib import Path

    config = get_config()
    if not config:
        raise NuvemFiscalError('Nuvem Fiscal não configurada.')

    path = Path(pfx_path)
    if not path.is_file():
        raise NuvemFiscalError(f'Arquivo de certificado não encontrado: {pfx_path}')

    document = normalize_cnpj(cpf_cnpj or config.emitter_document)
    if len(document) not in (11, 14):
        raise NuvemFiscalError('Informe CPF/CNPJ do emitente cadastrado na Nuvem Fiscal.')

    cert_b64 = base64.b64encode(path.read_bytes()).decode('ascii')
    _, payload = api_request(
        'PUT',
        f'/empresas/{document}/certificado',
        json_body={'certificado': cert_b64, 'password': password},
    )
    return payload if isinstance(payload, dict) else {'ok': True}


def consult_empresa_certificado(cpf_cnpj: str | None = None) -> dict:
    if is_mock_mode():
        config = get_config()
        return {
            'mock': True,
            'cpf_cnpj': normalize_cnpj(cpf_cnpj or (config.emitter_document if config else '')),
            'subject_name': 'CERTIFICADO SIMULADO',
            'not_valid_after': '2099-12-31T23:59:59Z',
        }

    config = get_config()
    if not config:
        raise NuvemFiscalError('Nuvem Fiscal não configurada.')
    document = normalize_cnpj(cpf_cnpj or config.emitter_document)
    _, payload = api_request('GET', f'/empresas/{document}/certificado')
    return payload


def consult_nfe(dfe_id: str) -> dict:
    if is_mock_mode():
        from api.services.nuvem_fiscal_mock import consult_mock_nfe
        return consult_mock_nfe(dfe_id)
    _, payload = api_request('GET', f'/nfe/{dfe_id}')
    return payload


def _now_brazil_iso() -> str:
    return datetime.now(ZoneInfo('America/Sao_Paulo')).strftime('%Y-%m-%dT%H:%M:%S%z')


def _money(value) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal('0.01')))


def resolve_emitter_document(invoice_request) -> str:
    config = get_config()
    seller = invoice_request.seller
    if seller and seller.document:
        doc = normalize_cnpj(seller.document)
        if len(doc) in (11, 14):
            return doc
    return config.emitter_document if config else ''


def build_nfe_payload(invoice_request) -> dict:
    from api.models import InvoiceRequest

    if not isinstance(invoice_request, InvoiceRequest):
        raise NuvemFiscalError('Solicitação de NF-e inválida.')

    config = get_config()
    if not config:
        raise NuvemFiscalError('Nuvem Fiscal não configurada.')

    order = invoice_request.order
    order.items.select_related('product').all()  # noqa: prefetch hint for caller
    items = list(order.items.all())
    if not items:
        raise NuvemFiscalError('Pedido sem itens para emissão de NF-e.')

    emitter_document = resolve_emitter_document(invoice_request)
    dest_uf = (order.shipping_state or 'SP').strip().upper()[:2]
    dest_cep = normalize_cnpj(order.shipping_zip or '')[:8] or '01310100'
    cep_data = lookup_cep(dest_cep)
    dest_city_ibge = str(cep_data.get('codigo_ibge') or config.emitter_city_ibge)
    dest_city = (cep_data.get('municipio') or order.shipping_city or 'Sao Paulo')[:60]
    dest_street = (order.shipping_address or 'Endereco nao informado')[:60]
    id_dest = 1 if dest_uf == config.emitter_uf else 2
    cfop = config.cfop if id_dest == 1 else ('6102' if config.cfop == '5102' else config.cfop)

    det = []
    total_prod = Decimal('0')
    for idx, item in enumerate(items, start=1):
        subtotal = Decimal(str(item.subtotal or 0))
        total_prod += subtotal
        qty = float(item.quantity or 1)
        unit = _money(subtotal / qty) if qty else _money(subtotal)
        sku = item.product_sku or str(item.product_id or idx)
        det.append({
            'nItem': idx,
            'prod': {
                'cProd': str(sku)[:60],
                'cEAN': 'SEM GTIN',
                'cEANTrib': 'SEM GTIN',
                'xProd': (item.product_name or 'Peca automotiva')[:120],
                'NCM': config.default_ncm,
                'CFOP': cfop,
                'uCom': 'UN',
                'qCom': qty,
                'vUnCom': unit,
                'vProd': _money(subtotal),
                'uTrib': 'UN',
                'qTrib': qty,
                'vUnTrib': unit,
                'indTot': 1,
            },
            'imposto': {
                'ICMS': {
                    'ICMSSN102': {
                        'orig': 0,
                        'CSOSN': '102',
                    },
                },
                'PIS': {'PISNT': {'CST': '07'}},
                'COFINS': {'COFINSNT': {'CST': '07'}},
            },
        })

    shipping = Decimal(str(order.shipping_fee or 0))
    discount = Decimal(str(order.discount_amount or 0))
    total_nf = total_prod + shipping - discount
    if total_nf < 0:
        total_nf = Decimal('0')

    dest_name = invoice_request.company_name[:60]
    if config.sandbox:
        dest_name = HOMOLOG_DEST_NAME

    payload = {
        'ambiente': config.ambiente,
        'referencia': f'galelugi-inv-{invoice_request.id}',
        'infNFe': {
            'versao': '4.00',
            'ide': {
                'cUF': UF_IBGE.get(config.emitter_uf, 35),
                'natOp': 'Venda de mercadoria',
                'mod': 55,
                'serie': 1,
                'nNF': invoice_request.id,
                'dhEmi': _now_brazil_iso(),
                'tpNF': 1,
                'idDest': id_dest,
                'cMunFG': config.emitter_city_ibge,
                'tpImp': 1,
                'tpEmis': 1,
                'tpAmb': config.tp_amb,
                'finNFe': 1,
                'indFinal': 1,
                'indPres': 2,
                'procEmi': 0,
                'verProc': 'Galelugi1.0',
            },
            'emit': _emit_identification(emitter_document),
            'dest': {
                'CNPJ': invoice_request.cnpj,
                'xNome': dest_name,
                'indIEDest': 9,
                'email': (invoice_request.company_email or invoice_request.user.email or '')[:60],
                'enderDest': {
                    'xLgr': dest_street,
                    'nro': 'S/N',
                    'xBairro': 'Centro',
                    'cMun': dest_city_ibge,
                    'xMun': dest_city,
                    'UF': dest_uf,
                    'CEP': dest_cep,
                    'cPais': '1058',
                    'xPais': 'Brasil',
                },
            },
            'det': det,
            'total': {
                'ICMSTot': {
                    'vBC': 0.0,
                    'vICMS': 0.0,
                    'vICMSDeson': 0.0,
                    'vFCP': 0.0,
                    'vBCST': 0.0,
                    'vST': 0.0,
                    'vFCPST': 0.0,
                    'vFCPSTRet': 0.0,
                    'vProd': _money(total_prod),
                    'vFrete': _money(shipping),
                    'vSeg': 0.0,
                    'vDesc': _money(discount),
                    'vII': 0.0,
                    'vIPI': 0.0,
                    'vIPIDevol': 0.0,
                    'vPIS': 0.0,
                    'vCOFINS': 0.0,
                    'vOutro': 0.0,
                    'vNF': _money(total_nf),
                },
            },
            'transp': {'modFrete': 9 if order.delivery_method == 'pickup' else 0},
            'pag': {
                'detPag': [{
                    'tPag': '99',
                    'xPag': 'Outros',
                    'vPag': _money(total_nf),
                }],
            },
            'infAdic': {
                'infCpl': f'Pedido Galelugi #{order.id}. Documento emitido via integracao Nuvem Fiscal.',
            },
        },
    }
    return payload


def wait_for_authorization(dfe_id: str, *, attempts: int = 20, delay_seconds: float = 2.0) -> dict:
    last = {}
    for _ in range(attempts):
        last = consult_nfe(dfe_id)
        status = (last.get('status') or '').lower()
        if status in {'autorizado', 'rejeitado', 'denegado', 'erro', 'cancelado'}:
            return last
        time.sleep(delay_seconds)
    return last


def emit_invoice_nfe(invoice_request) -> dict:
    """Emite NF-e na Nuvem Fiscal e retorna o documento (Dfe)."""
    if is_mock_mode():
        from api.services.nuvem_fiscal_mock import apply_mock_emission
        if invoice_request.nuvem_fiscal_id and invoice_request.nuvem_fiscal_status == 'autorizado':
            return consult_nfe(invoice_request.nuvem_fiscal_id)
        logger.info('NF-e simulada para solicitação #%s', invoice_request.id)
        return apply_mock_emission(invoice_request)

    if invoice_request.nuvem_fiscal_id and invoice_request.nuvem_fiscal_status == 'autorizado':
        return consult_nfe(invoice_request.nuvem_fiscal_id)

    payload = build_nfe_payload(invoice_request)
    _, dfe = api_request('POST', '/nfe', json_body=payload)
    dfe_id = dfe.get('id')
    if not dfe_id:
        raise NuvemFiscalError('Nuvem Fiscal não retornou ID do documento.')

    invoice_request.nuvem_fiscal_id = dfe_id
    invoice_request.nuvem_fiscal_status = dfe.get('status') or 'pendente'
    invoice_request.save(update_fields=['nuvem_fiscal_id', 'nuvem_fiscal_status', 'updated_at'])

    if invoice_request.nuvem_fiscal_status == 'pendente':
        dfe = wait_for_authorization(dfe_id)

    invoice_request.nuvem_fiscal_status = dfe.get('status') or invoice_request.nuvem_fiscal_status
    if dfe.get('chave'):
        invoice_request.nuvem_fiscal_chave = dfe['chave']
    if dfe.get('numero'):
        invoice_request.invoice_number = str(dfe['numero'])
    elif dfe.get('chave'):
        invoice_request.invoice_number = dfe['chave']

    status = (invoice_request.nuvem_fiscal_status or '').lower()
    if status == 'autorizado':
        invoice_request.status = 'issued'
        backend = getattr(settings, 'BACKEND_URL', 'http://127.0.0.1:8000').rstrip('/')
        invoice_request.invoice_url = f'{backend}/api/v1/invoices/{invoice_request.id}/nfe-pdf/'
    elif status in {'rejeitado', 'denegado', 'erro'}:
        auth = dfe.get('autorizacao') or {}
        motivo = auth.get('motivo_status') or auth.get('xMotivo') or dfe.get('status')
        invoice_request.admin_notes = f'Nuvem Fiscal: {motivo}'[:2000]
        raise NuvemFiscalError(
            f'NF-e não autorizada ({status}): {motivo}',
            code=status,
            payload=dfe,
        )

    invoice_request.save()
    return dfe


def test_connection(cnpj: str | None = None) -> dict:
    """Valida credenciais OAuth e consulta status SEFAZ da empresa."""
    if is_mock_mode():
        config = get_config()
        target = normalize_cnpj(cnpj or (config.emitter_document if config else ''))
        return {
            'ok': True,
            'mock': True,
            'sandbox': True,
            'api_base': 'mock://nuvem-fiscal',
            'emitter_document': config.emitter_document if config else target,
            'emitter_type': 'cpf' if config and config.emitter_is_cpf else 'cnpj',
            'token_preview': 'mock-token...',
            'sefaz_status': sefaz_status(target),
            'message': 'Modo simulação ativo (NUVEM_FISCAL_MOCK=true). Nenhuma chamada à API real.',
        }

    config = get_config()
    if not config:
        return {
            'ok': False,
            'message': 'Configure NUVEM_FISCAL_CLIENT_ID, NUVEM_FISCAL_CLIENT_SECRET e NUVEM_FISCAL_EMITTER_CPF ou EMITTER_CNPJ.',
        }
    token = get_access_token(force_refresh=True)
    target = normalize_cnpj(cnpj or config.emitter_document)
    sefaz = sefaz_status(target)
    return {
        'ok': True,
        'sandbox': config.sandbox,
        'api_base': config.api_base,
        'emitter_document': config.emitter_document,
        'emitter_type': 'cpf' if config.emitter_is_cpf else 'cnpj',
        'token_preview': f'{token[:12]}...',
        'sefaz_status': sefaz,
        'message': 'Conexão OK. Verifique se a empresa e o certificado estão cadastrados no console Nuvem Fiscal.',
    }
