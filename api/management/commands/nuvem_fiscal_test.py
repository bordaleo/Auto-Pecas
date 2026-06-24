from django.core.management.base import BaseCommand

from api.services.nuvem_fiscal_service import NuvemFiscalError, get_config, is_mock_mode, test_connection


class Command(BaseCommand):
    help = 'Testa credenciais OAuth e status SEFAZ na Nuvem Fiscal.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cnpj',
            help='CNPJ do emitente para consultar status SEFAZ (padrão: NUVEM_FISCAL_EMITTER_CNPJ).',
        )

    def handle(self, *args, **options):
        config = get_config()
        if not config:
            self.stderr.write(self.style.ERROR(
                'Nuvem Fiscal não configurada.\n'
                'Defina no .env:\n'
                '  NUVEM_FISCAL_CLIENT_ID\n'
                '  NUVEM_FISCAL_CLIENT_SECRET\n'
                '  NUVEM_FISCAL_EMITTER_CPF ou NUVEM_FISCAL_EMITTER_CNPJ\n'
                '  NUVEM_FISCAL_SANDBOX=true\n'
            ))
            return

        if is_mock_mode():
            self.stdout.write(self.style.WARNING('NUVEM_FISCAL_MOCK=true — API real desativada (respostas simuladas)'))

        self.stdout.write(f'Ambiente: {"sandbox" if config.sandbox else "produção"}')
        self.stdout.write(f'API: {config.api_base}')
        self.stdout.write(f'Emitente: {config.emitter_document} ({ "CPF" if config.emitter_is_cpf else "CNPJ" })')

        try:
            result = test_connection(options.get('cnpj'))
        except NuvemFiscalError as exc:
            self.stderr.write(self.style.ERROR(f'Falha: {exc}'))
            return

        if not result.get('ok'):
            self.stderr.write(self.style.ERROR(result.get('message', 'Erro desconhecido')))
            return

        self.stdout.write(self.style.SUCCESS(result.get('message', 'OK')))
        self.stdout.write(f"Token: {result.get('token_preview')}")
        sefaz = result.get('sefaz_status') or {}
        self.stdout.write(f"SEFAZ: {sefaz}")
