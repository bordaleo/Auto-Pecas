"""
Backend SMTP com timeout configurável e melhor tratamento de erros de rede.
Útil no Render, onde conexões SMTP podem ter restrições de rede.

NOTA IMPORTANTE: O Render bloqueia conexões SMTP para Gmail (erro 101).
SOLUÇÃO: Use SendGrid SMTP no Render - ainda é SMTP, mas funciona!
Configuração SendGrid:
  SMTP_HOST=smtp.sendgrid.net
  SMTP_PORT=587
  SMTP_USER=apikey
  SMTP_PASSWORD=SG.sua-api-key
  SMTP_FROM_EMAIL=seu-email-verificado@sendgrid.com
"""
import socket
import logging
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend

logger = logging.getLogger(__name__)


class EmailBackend(SMTPEmailBackend):
    def __init__(self, timeout=None, fail_silently=False, **kwargs):
        timeout = timeout if timeout is not None else getattr(settings, 'EMAIL_TIMEOUT', 30)
        # Timeout mínimo de 10 segundos (evita esperar muito em caso de bloqueio)
        if timeout < 10:
            timeout = 10
        super().__init__(timeout=timeout, fail_silently=fail_silently, **kwargs)
    
    def open(self):
        """
        Sobrescreve o método open para adicionar melhor tratamento de erros de rede
        e logging detalhado para debug no Render.
        """
        if self.connection:
            return False
        
        host = getattr(self, 'host', None)
        port = getattr(self, 'port', None)
        use_tls = getattr(self, 'use_tls', False)
        use_ssl = getattr(self, 'use_ssl', False)
        
        logger.info(f"Tentando conectar ao SMTP {host}:{port} (TLS={use_tls}, SSL={use_ssl}, timeout={self.timeout})")
        
        try:
            # Usa a implementação padrão do Django (mais confiável)
            result = super().open()
            if result:
                logger.info(f"Conexão SMTP estabelecida com sucesso para {host}:{port}")
            return result
            
        except (socket.gaierror, socket.error, OSError, TimeoutError) as e:
            error_code = getattr(e, 'errno', None)
            error_msg = f"Erro de rede ao conectar ao SMTP {host}:{port} (errno={error_code}): {e}"
            logger.error(error_msg)
            
            # Mensagem específica para erro 101 (Network is unreachable)
            if error_code == 101:
                logger.error(
                    "ERRO 101: Network is unreachable - Verifique se está usando SendGrid SMTP no Render. "
                    "Gmail SMTP é bloqueado pelo Render."
                )
            
            # Mensagem específica para timeout
            if 'timed out' in str(e).lower() or isinstance(e, TimeoutError):
                logger.error(
                    f"TIMEOUT: Conexão SMTP expirou após {self.timeout}s. "
                    f"O Render pode estar bloqueando conexões SMTP. "
                    f"O email será enviado de forma assíncrona para não bloquear o registro. "
                    f"Alternativas: use API REST do Brevo ou outro serviço de email compatível com Render."
                )
            
            if not self.fail_silently:
                raise
            return False
        except Exception as e:
            error_msg = f"Erro inesperado ao conectar ao SMTP {host}:{port}: {type(e).__name__}: {e}"
            logger.error(error_msg, exc_info=True)
            if not self.fail_silently:
                raise
            return False