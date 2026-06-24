"""Normaliza login curto (admin, sandroni) para e-mail completo."""

LOGIN_EMAIL_ALIASES = {
    'admin': 'admin@admin.com',
    'sandroni': 'sandroni@sandroni.com',
}


def resolve_login_email(raw: str) -> str:
    value = (raw or '').strip().lower()
    if not value:
        return value
    if '@' in value:
        return value
    return LOGIN_EMAIL_ALIASES.get(value, value)
