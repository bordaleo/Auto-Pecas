"""Grupos de sinônimos para unificar buscas fragmentadas."""
from __future__ import annotations

import re

TOKEN_SPLIT = re.compile(r'\s+')

# Cada grupo: termos equivalentes (minúsculas, sem acento opcional via contains)
SYNONYM_GROUPS: list[frozenset[str]] = [
    frozenset({
        'pastilha', 'pastilhas', 'pastilha de freio', 'pastilhas de freio',
        'freio dianteiro', 'freio traseiro', 'disco de freio', 'kit freio',
    }),
    frozenset({
        'filtro de ar', 'filtro ar', 'filtro de ar do motor', 'elemento filtro ar',
    }),
    frozenset({
        'filtro de oleo', 'filtro de óleo', 'filtro oleo', 'filtro óleo', 'filtro lubrificante',
    }),
    frozenset({
        'amortecedor', 'amortecedores', 'shock', 'amortecedor dianteiro', 'amortecedor traseiro',
    }),
    frozenset({
        'correia dentada', 'correia do motor', 'kit correia', 'tensor correia',
    }),
    frozenset({
        'vela', 'velas', 'vela de ignição', 'vela de ignicao', 'vela ignição',
    }),
    frozenset({
        'bateria', 'bateria automotiva', 'bateria de carro',
    }),
    frozenset({
        'embreagem', 'kit embreagem', 'disco embreagem', 'platô embreagem',
    }),
    frozenset({
        'radiador', 'radiador motor', 'água radiador', 'agua radiador',
    }),
    frozenset({
        'coxim', 'coxim motor', 'calço motor', 'suporte motor',
    }),
]

_TERM_TO_GROUP: dict[str, frozenset[str]] = {}
for group in SYNONYM_GROUPS:
    for term in group:
        _TERM_TO_GROUP[term.lower()] = group


def _normalize_phrase(text: str) -> str:
    return (text or '').strip().lower()


def find_phrase_synonyms(q: str) -> list[str] | None:
    """Se a frase inteira pertence a um grupo, retorna todos os termos do grupo."""
    key = _normalize_phrase(q)
    if not key:
        return None
    group = _TERM_TO_GROUP.get(key)
    if group:
        return sorted(group, key=len, reverse=True)
    for term, grp in _TERM_TO_GROUP.items():
        if len(term) >= 4 and (key == term or key in term or term in key):
            return sorted(grp, key=len, reverse=True)
    return None


def expand_token(token: str) -> list[str]:
    """Expande um token para sinônimos do mesmo grupo."""
    key = _normalize_phrase(token)
    if not key:
        return []
    group = _TERM_TO_GROUP.get(key)
    if group:
        return sorted(group, key=len, reverse=True)
    for term, grp in _TERM_TO_GROUP.items():
        if len(term) >= 3 and (key in term or term in key):
            return sorted(grp, key=len, reverse=True)
    return [token]


def tokenize_query(q: str) -> list[str]:
    raw = (q or '').strip()
    if not raw:
        return []
    parts = TOKEN_SPLIT.split(raw)
    return [p for p in parts if len(p) >= 2]
