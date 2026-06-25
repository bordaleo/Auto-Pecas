"""Normaliza login curto (admin, sandroni) para e-mail completo."""

LOGIN_EMAIL_ALIASES = {
    'admin': 'admin@admin.com',
    'sandroni': 'sandroni@sandroni.com',
    'admin@admin': 'admin@admin.com',
    'sandroni@sandroni': 'sandroni@sandroni.com',
}


def resolve_login_email(raw: str) -> str:
    value = (raw or '').strip().lower()
    if not value:
        return value
    if value in LOGIN_EMAIL_ALIASES:
        return LOGIN_EMAIL_ALIASES[value]
    if '@' not in value:
        return LOGIN_EMAIL_ALIASES.get(value, value)
    local, _, domain = value.partition('@')
    if local == 'sandroni' and domain in ('sandroni', 'sandroni.com'):
        return 'sandroni@sandroni.com'
    if local == 'admin' and domain == 'admin':
        return 'admin@admin.com'
    return value
