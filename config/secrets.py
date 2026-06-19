"""Carrega segredos de credentials.py ou variáveis de ambiente."""
from __future__ import annotations

import os
from typing import Any


def cfg(name: str, default: Any = None) -> Any:
    """Prioridade: env > credentials.py > default."""
    val = os.getenv(name)
    if val not in (None, ''):
        return val
    try:
        from config import credentials

        cred = getattr(credentials, name, None)
        if cred not in (None, ''):
            return cred
    except ImportError:
        pass
    return default


def cfg_bool(name: str, default: bool = False) -> bool:
    val = cfg(name, None)
    if val is None:
        return default
    return str(val).lower() in ('1', 'true', 'yes')
