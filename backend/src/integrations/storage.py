"""Storage de objetos (MinIO/S3). Upload via URL pré-assinada; prefixo por tenant."""

import logging
from datetime import timedelta

from minio import Minio

from ..core.config import settings

log = logging.getLogger("storage")

_client: Minio | None = None
_public_client: Minio | None = None


def _get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def _get_public_client() -> Minio:
    """Cliente que assina URLs com o endpoint público (acessível pelo browser)."""
    global _public_client
    if _public_client is None:
        _public_client = Minio(
            settings.minio_public_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _public_client


def ensure_bucket() -> None:
    client = _get_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
        log.info("Bucket '%s' criado.", settings.minio_bucket)


def object_key(workspace_id: str, doc_id: str, filename: str) -> str:
    return f"{workspace_id}/documents/{doc_id}/{filename}"


def presigned_put(key: str, expires_min: int = 15) -> str:
    return _get_public_client().presigned_put_object(
        settings.minio_bucket, key, expires=timedelta(minutes=expires_min)
    )


def presigned_get(key: str, expires_min: int = 60) -> str:
    return _get_public_client().presigned_get_object(
        settings.minio_bucket, key, expires=timedelta(minutes=expires_min)
    )


def get_bytes(key: str) -> bytes:
    resp = _get_client().get_object(settings.minio_bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()
