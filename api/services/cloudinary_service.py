from __future__ import annotations

import base64
import hashlib
import logging

import cloudinary.api
import cloudinary.uploader
from cloudinary.exceptions import NotFound
from django.conf import settings

logger = logging.getLogger(__name__)


def is_http_url(value):
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _decode_image_bytes(raw_value: str) -> bytes:
    if raw_value.startswith("data:image"):
        if "," not in raw_value:
            raise ValueError("Data URI inválida.")
        b64 = raw_value.split(",", 1)[1].strip()
    else:
        b64 = raw_value.split("base64,", 1)[-1].strip()
    return base64.b64decode(b64, validate=True)


def get_existing_cloudinary_image_secure_url(public_id: str) -> str | None:
    if not settings.CLOUDINARY_ENABLED or not public_id:
        return None
    try:
        info = cloudinary.api.resource(public_id, resource_type="image")
        return info.get("secure_url")
    except NotFound:
        return None
    except Exception as e:
        logger.warning("Cloudinary resource %s: %s", public_id, e)
        return None


def upload_image_if_needed(image_value, folder="sandroni/products"):
    if not image_value:
        return image_value
    if not isinstance(image_value, str):
        raise ValueError("Formato de imagem inválido.")
    raw = image_value.strip()
    if not raw:
        return raw
    if is_http_url(raw):
        return raw
    if not settings.CLOUDINARY_ENABLED:
        raise ValueError("Cloudinary não configurado.")

    image_bytes = _decode_image_bytes(raw)
    content_hash = hashlib.sha256(image_bytes).hexdigest()
    prefix = (folder or "sandroni/products").strip().strip("/")
    public_id = f"{prefix}/{content_hash}"

    existing = get_existing_cloudinary_image_secure_url(public_id)
    if existing:
        return existing

    if raw.startswith("data:image"):
        data_uri = raw
    else:
        data_uri = f"data:image/jpeg;base64,{raw.split('base64,', 1)[-1].strip()}"

    result = cloudinary.uploader.upload(
        data_uri,
        public_id=public_id,
        resource_type="image",
        unique_filename=False,
        overwrite=True,
        invalidate=True,
        use_filename=False,
    )
    url = result.get("secure_url")
    if not url:
        raise ValueError("Falha no upload Cloudinary.")
    return url
