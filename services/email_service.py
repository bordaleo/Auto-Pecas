import logging
import os

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

logger = logging.getLogger(__name__)


def send_email(to_email, subject, html_content, text_content=None, tags=None):
    """
    Envia email transacional usando apenas a API da Brevo.

    Returns:
        bool: True se enviado com sucesso, False em caso de erro/configuração ausente.
    """
    api_key = os.getenv("BREVO_API_KEY")
    from_email = os.getenv("SMTP_FROM_EMAIL")
    sender_name = os.getenv("SMTP_FROM_NAME", "Galelugi Peças")

    if not api_key:
        logger.error("BREVO_API_KEY não configurada. Email não enviado para %s.", to_email)
        return False

    if not from_email:
        logger.error("SMTP_FROM_EMAIL não configurado. Email não enviado para %s.", to_email)
        return False

    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = api_key
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

        payload = {
            "to": [{"email": to_email}],
            "sender": {"name": sender_name, "email": from_email},
            "subject": subject,
            "html_content": html_content,
        }
        if text_content:
            payload["text_content"] = text_content
        if tags:
            payload["tags"] = tags

        email = sib_api_v3_sdk.SendSmtpEmail(**payload)

        api_instance.send_transac_email(email)
        logger.info("Email enviado com sucesso para %s.", to_email)
        return True
    except ApiException as exc:
        logger.error("Erro da API Brevo ao enviar email para %s: %s", to_email, exc)
    except Exception as exc:
        logger.error("Erro inesperado ao enviar email para %s: %s", to_email, exc, exc_info=True)
    return False
