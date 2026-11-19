"""Object storage abstraction (S3/MinIO with local filesystem fallback)."""

import logging
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FileStorage:
    """Stores exported PDF/DOCX artifacts in S3-compatible storage or local disk."""

    def __init__(self) -> None:
        self._s3_client = None
        self._s3_checked = False

    def _get_s3(self):
        if self._s3_checked:
            return self._s3_client
        self._s3_checked = True
        settings = get_settings()
        if settings.S3_ENDPOINT_URL and settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY:
            try:
                import boto3
                from botocore.exceptions import ClientError

                client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.S3_ACCESS_KEY,
                    aws_secret_access_key=settings.S3_SECRET_KEY,
                    region_name=settings.S3_REGION,
                )
                try:
                    client.head_bucket(Bucket=settings.S3_BUCKET_NAME)
                except ClientError:
                    client.create_bucket(Bucket=settings.S3_BUCKET_NAME)
                self._s3_client = client
            except Exception as exc:
                logger.warning("S3 unavailable, falling back to local storage: %s", exc)
                self._s3_client = None
        return self._s3_client

    def _local_root(self) -> Path:
        root = Path(get_settings().LOCAL_STORAGE_DIR)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def save_bytes(self, object_key: str, data: bytes, content_type: str) -> str:
        """Persist bytes under `object_key` and return the storage key."""
        s3 = self._get_s3()
        settings = get_settings()
        if s3 is not None:
            try:
                s3.put_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=object_key,
                    Body=data,
                    ContentType=content_type,
                )
                return object_key
            except Exception as exc:
                logger.warning("Failed to upload to S3, saving locally: %s", exc)

        target = self._local_root() / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return object_key

    def read_bytes(self, object_key: str) -> Optional[bytes]:
        """Load bytes for `object_key`, or return None if missing."""
        s3 = self._get_s3()
        settings = get_settings()
        if s3 is not None:
            try:
                resp = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=object_key)
                return resp["Body"].read()
            except Exception:
                pass

        target = self._local_root() / object_key
        if target.exists():
            return target.read_bytes()
        return None

    def delete_object(self, object_key: str) -> None:
        """Delete a single object from storage."""
        s3 = self._get_s3()
        settings = get_settings()
        if s3 is not None:
            try:
                s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=object_key)
            except Exception:
                pass

        target = self._local_root() / object_key
        if target.exists():
            target.unlink(missing_ok=True)

    def delete_prefix(self, prefix: str) -> None:
        """Delete all objects belonging to a user prefix on account deletion."""
        s3 = self._get_s3()
        settings = get_settings()
        if s3 is not None:
            try:
                resp = s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME, Prefix=prefix)
                objects = [{"Key": obj["Key"]} for obj in resp.get("Contents", [])]
                if objects:
                    s3.delete_objects(Bucket=settings.S3_BUCKET_NAME, Delete={"Objects": objects})
            except Exception:
                pass

        local_dir = self._local_root() / prefix
        if local_dir.exists() and local_dir.is_dir():
            for path in sorted(local_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink(missing_ok=True)
                elif path.is_dir():
                    try:
                        path.rmdir()
                    except OSError:
                        pass
            try:
                local_dir.rmdir()
            except OSError:
                pass


file_storage = FileStorage()
