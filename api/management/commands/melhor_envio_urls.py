from django.core.management.base import BaseCommand

from api.services.melhor_envio_oauth_service import melhor_envio_authorize_url, melhor_envio_redirect_uri


class Command(BaseCommand):
    help = 'Exibe as URLs para cadastrar o app no Melhor Envio (Área Dev).'

    def handle(self, *args, **options):
        redirect = melhor_envio_redirect_uri()
        base = redirect.replace('/api/v1/integrations/melhor-envio/callback/', '').rstrip('/')

        self.stdout.write(self.style.SUCCESS('URLs para o formulário Melhor Envio (HTTPS):'))
        self.stdout.write('')
        self.stdout.write('URL do ambiente para testes:')
        self.stdout.write(f'  {base}')
        self.stdout.write('')
        self.stdout.write('URL de redirecionamento após autorização:')
        self.stdout.write(f'  {redirect}')
        self.stdout.write('')
        self.stdout.write('Site da plataforma (se pedirem):')
        self.stdout.write(f'  {base}')
        self.stdout.write('')

        auth = melhor_envio_authorize_url()
        if auth:
            self.stdout.write('Link para autorizar (após salvar Client ID/Secret):')
            self.stdout.write(f'  {auth}')
        else:
            self.stdout.write(self.style.WARNING(
                'Defina MELHOR_ENVIO_CLIENT_ID e MELHOR_ENVIO_CLIENT_SECRET em credentials.py'
            ))
