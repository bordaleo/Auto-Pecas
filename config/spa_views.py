"""Serve o build do React (Vite) em produção — mesmo host que a API."""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404


def _dist_dir() -> Path:
    return Path(getattr(settings, 'FRONTEND_DIST', settings.BASE_DIR / 'frontend' / 'dist'))


def _safe_path(rel_path: str) -> Path | None:
    base = _dist_dir().resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base)):
        return None
    return target


def serve_spa_asset(request, path):
    file_path = _safe_path(f'assets/{path}')
    if not file_path or not file_path.is_file():
        raise Http404()
    return FileResponse(open(file_path, 'rb'))


def serve_spa(request, path=''):
    dist = _dist_dir()
    index = dist / 'index.html'
    if not index.is_file():
        raise Http404('Frontend não encontrado. Rode npm run build no frontend.')

    if path:
        file_path = _safe_path(path)
        if file_path and file_path.is_file():
            return FileResponse(open(file_path, 'rb'))

    return FileResponse(open(index, 'rb'), content_type='text/html; charset=utf-8')
