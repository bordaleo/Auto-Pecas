"""Utilitários compartilhados da API."""


def is_superadmin(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)


def normalize_cnpj(value: str) -> str:
    return ''.join(ch for ch in (value or '') if ch.isdigit())


def validate_cnpj(cnpj: str) -> bool:
    """Valida dígitos verificadores do CNPJ brasileiro."""
    digits = normalize_cnpj(cnpj)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    def calc(weights, base):
        total = sum(int(d) * w for d, w in zip(base, weights))
        remainder = total % 11
        return '0' if remainder < 2 else str(11 - remainder)

    first = calc([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], digits[:12])
    second = calc([6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], digits[:12] + first)
    return digits[-2:] == first + second


def format_cnpj(cnpj: str) -> str:
    digits = normalize_cnpj(cnpj)
    if len(digits) != 14:
        return cnpj
    return f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}'
