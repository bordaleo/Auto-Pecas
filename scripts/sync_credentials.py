#!/usr/bin/env python
"""Gera config/credentials.py a partir do .env local."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / '.env'
OUT = ROOT / 'config' / 'credentials.py'

KEYS = [
    'SECRET_KEY',
    'MERCADOPAGO_ACCESS_TOKEN',
    'MERCADOPAGO_PUBLIC_KEY',
    'MERCADOPAGO_WEBHOOK_SECRET',
    'CLOUDINARY_CLOUD_NAME',
    'CLOUDINARY_API_KEY',
    'CLOUDINARY_API_SECRET',
    'SMTP_HOST',
    'SMTP_PORT',
    'SMTP_USER',
    'SMTP_PASSWORD',
    'SMTP_FROM_EMAIL',
    'SMTP_USE_SSL',
    'BREVO_API_KEY',
    'PAINEL_GATE_PASSWORD',
]

ALIASES = {
    'SECRET_KEY': ['DJANGO_SECRET_KEY'],
}


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def main() -> None:
    env = parse_env(ENV)
    if not env:
        raise SystemExit(f'.env não encontrado em {ENV}')

    lines = [
        '"""Segredos gerados a partir do .env — commitar só em repo privado."""',
        '',
    ]
    for key in KEYS:
        value = env.get(key)
        if value is None:
            for alt in ALIASES.get(key, []):
                if alt in env:
                    value = env[alt]
                    break
        if value is None:
            continue
        if value.lower() in ('true', 'false'):
            lines.append(f'{key} = {value.lower() == "true"}')
        elif value.isdigit():
            lines.append(f'{key} = {value}')
        else:
            escaped = value.replace("'", "\\'")
            lines.append(f"{key} = '{escaped}'")

    OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Gerado: {OUT}')


if __name__ == '__main__':
    main()
