"""Handler de logging que envia ERROR para alertas operacionais.

Use ``logger.error(..., extra={"skip_ops_alert": True})`` quando o erro for esperado
(ex.: validação forte) mas precisar permanecer em nível ERROR no arquivo/console.
"""
import logging

from api.services.ops_alerts import alert_from_log_record


class OpsAlertLogHandler(logging.Handler):
    """Encaminha registos ERROR (e CRITICAL) para ``ops_alerts``."""

    def __init__(self, level: int = logging.ERROR):
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno < logging.ERROR:
                return
            alert_from_log_record(record)
        except Exception:
            self.handleError(record)
