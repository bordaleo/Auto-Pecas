from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from api.services.nuvem_fiscal_service import (
    NuvemFiscalError,
    consult_empresa_certificado,
    get_config,
    sefaz_status,
    test_connection,
    upload_empresa_certificado,
)


class Command(BaseCommand):
    help = 'Envia certificado A1 (.pfx) para a empresa na Nuvem Fiscal (sandbox/produção).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pfx',
            default=str(Path(settings.BASE_DIR) / 'media' / 'certificado_teste_a1.pfx'),
            help='Caminho do arquivo .pfx',
        )
        parser.add_argument('--password', required=True, help='Senha do certificado')
        parser.add_argument('--cpf-cnpj', help='CPF/CNPJ (padrão: emitente configurado)')
        parser.add_argument('--skip-test', action='store_true', help='Não roda teste SEFAZ após upload')

    def handle(self, *args, **options):
        config = get_config()
        if not config:
            self.stderr.write(self.style.ERROR('Nuvem Fiscal não configurada.'))
            return

        pfx = options['pfx']
        password = options['password']
        doc = options.get('cpf_cnpj') or config.emitter_document

        self.stdout.write(f'Ambiente: {"sandbox" if config.sandbox else "produção"}')
        self.stdout.write(f'Emitente: {doc}')
        self.stdout.write(f'Certificado: {pfx}')

        try:
            result = upload_empresa_certificado(pfx, password, cpf_cnpj=doc)
            self.stdout.write(self.style.SUCCESS('Certificado enviado com sucesso.'))
            if result:
                self.stdout.write(str(result))
            cert = consult_empresa_certificado(doc)
            if cert:
                self.stdout.write(f"Válido até: {cert.get('not_valid_after', '—')}")
                self.stdout.write(f"Titular: {cert.get('subject_name') or cert.get('nome_razao_social', '—')}")
        except NuvemFiscalError as exc:
            self.stderr.write(self.style.ERROR(f'Falha no upload: {exc}'))
            return

        if options.get('skip_test'):
            return

        try:
            check = test_connection(doc)
            if check.get('ok'):
                self.stdout.write(self.style.SUCCESS(check.get('message', 'Conexão OK')))
                self.stdout.write(f"SEFAZ: {check.get('sefaz_status')}")
            else:
                self.stderr.write(self.style.WARNING(check.get('message', 'Teste incompleto')))
        except NuvemFiscalError as exc:
            self.stderr.write(self.style.WARNING(f'Teste pós-upload: {exc}'))
