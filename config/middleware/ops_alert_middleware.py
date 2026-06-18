"""Alerta em exceções não tratadas durante o pedido HTTP."""
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from api.services.ops_alerts import alert_unhandled_request_exception


class OpsAlertMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if getattr(settings, "DEBUG", False) and not getattr(settings, "OPS_ALERT_IN_DEBUG", False):
            return None
        if not (
            getattr(settings, "OPS_ALERT_WEBHOOK_URL", None)
            or getattr(settings, "OPS_ALERT_EMAIL", None)
        ):
            return None
        try:
            alert_unhandled_request_exception(request, exception)
        except Exception:
            pass
        return None
