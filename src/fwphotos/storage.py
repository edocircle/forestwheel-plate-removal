"""Object Storage (S3-compatible Hetzner Object Storage) and Local Storage abstraction."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)


def load_dotenv_if_present(env_path: Path = Path(".env")) -> dict[str, str]:
    """Load key=value pairs from a local .env file if it exists (without overriding existing env vars)."""
    loaded: dict[str, str] = {}
    if not env_path.is_file():
        return loaded
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        val = v.strip().strip('"').strip("'")
        if key:
            loaded[key] = val
            os.environ.setdefault(key, val)
    return loaded


def scope_prefix(user_id: int | None, is_guest_trial: bool = False) -> str:
    """Return the storage key prefix for an authenticated user or guest trial workspace."""
    if is_guest_trial or user_id is None:
        return "guest_trial"
    return f"accounts/user_{int(user_id)}"


class PhotoStorage:
    """Abstract interface for storing and retrieving vehicle photos and custom assets."""

    is_s3: bool = False

    def exists(self, key: str) -> bool:
        raise NotImplementedError

    def read_bytes(self, key: str) -> bytes | None:
        raise NotImplementedError

    def write_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        raise NotImplementedError

    def delete_key(self, key: str) -> bool:
        raise NotImplementedError

    def delete_prefix(self, prefix: str) -> int:
        raise NotImplementedError

    def list_keys(self, prefix: str) -> list[str]:
        raise NotImplementedError

    def rename_prefix(self, old_prefix: str, new_prefix: str) -> int:
        raise NotImplementedError


class LocalPhotoStorage(PhotoStorage):
    """Local filesystem storage backend (default for local development and tests)."""

    is_s3: bool = False

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        clean = key.lstrip("/").replace("\\", "/")
        return self.base_dir / clean

    def exists(self, key: str) -> bool:
        return self._path_for(key).is_file()

    def read_bytes(self, key: str) -> bytes | None:
        p = self._path_for(key)
        if not p.is_file():
            return None
        return p.read_bytes()

    def write_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        p = self._path_for(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def delete_key(self, key: str) -> bool:
        p = self._path_for(key)
        if p.is_file():
            p.unlink()
            return True
        return False

    def delete_prefix(self, prefix: str) -> int:
        p = self._path_for(prefix)
        removed = 0
        if p.is_dir():
            for child in p.rglob("*"):
                if child.is_file():
                    removed += 1
            shutil.rmtree(p, ignore_errors=True)
            return removed
        parent = p.parent
        if parent.is_dir():
            norm_pref = prefix.strip("/")
            for child in list(parent.rglob("*")):
                if child.is_file():
                    rel = child.relative_to(self.base_dir).as_posix()
                    if rel.startswith(norm_pref):
                        child.unlink(missing_ok=True)
                        removed += 1
        return removed

    def list_keys(self, prefix: str) -> list[str]:
        norm_pref = prefix.strip("/")
        search_root = self._path_for(norm_pref)
        results: list[str] = []
        if search_root.is_dir():
            for p in sorted(search_root.rglob("*")):
                if p.is_file():
                    results.append(p.relative_to(self.base_dir).as_posix())
        return results

    def rename_prefix(self, old_prefix: str, new_prefix: str) -> int:
        old_keys = self.list_keys(old_prefix)
        moved = 0
        norm_old = old_prefix.rstrip("/") + "/"
        norm_new = new_prefix.rstrip("/") + "/"
        for k in old_keys:
            if not k.startswith(norm_old):
                continue
            new_k = norm_new + k[len(norm_old) :]
            data = self.read_bytes(k)
            if data is not None:
                self.write_bytes(new_k, data)
                self.delete_key(k)
                moved += 1
        return moved


class S3PhotoStorage(PhotoStorage):
    """S3-compatible Object Storage backend (Hetzner Object Storage) with bounded local LRU cache."""

    is_s3: bool = True

    def __init__(
        self,
        bucket: str,
        endpoint_url: str,
        region: str = "fsn1",
        access_key: str = "",
        secret_key: str = "",
        cache_dir: Path | None = None,
        local_cache_max_mb: int = 500,
        s3_client: Any | None = None,
    ) -> None:
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        self.region = region
        self.max_cache_bytes = max(0, int(local_cache_max_mb)) * 1024 * 1024
        self.cache_dir = (
            Path(cache_dir)
            if cache_dir is not None
            else Path(tempfile.gettempdir()) / "fwphotos_s3_cache"
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if s3_client is not None:
            self._client = s3_client
        else:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=Config(signature_version="s3v4"),
            )

    @staticmethod
    def _norm_key(key: str) -> str:
        return key.lstrip("/").replace("\\", "/")

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / self._norm_key(key)

    def _evict_cache_if_needed(self) -> None:
        if self.max_cache_bytes <= 0 or not self.cache_dir.exists():
            return
        files: list[tuple[float, int, Path]] = []
        total_size = 0
        for p in self.cache_dir.rglob("*"):
            if p.is_file():
                try:
                    st = p.stat()
                    total_size += st.st_size
                    files.append((st.st_mtime, st.st_size, p))
                except OSError:
                    continue
        if total_size <= self.max_cache_bytes:
            return
        # Evict oldest-accessed files first
        files.sort(key=lambda item: item[0])
        for _, sz, p in files:
            if total_size <= self.max_cache_bytes:
                break
            try:
                p.unlink(missing_ok=True)
                total_size -= sz
            except OSError:
                pass

    def _write_cache(self, key: str, data: bytes) -> None:
        if self.max_cache_bytes <= 0:
            return
        cp = self._cache_path(key)
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_bytes(data)
        self._evict_cache_if_needed()

    def exists(self, key: str) -> bool:
        norm = self._norm_key(key)
        cp = self._cache_path(norm)
        if cp.is_file():
            return True
        try:
            self._client.head_object(Bucket=self.bucket, Key=norm)
            return True
        except Exception:  # noqa: BLE001
            return False

    def read_bytes(self, key: str) -> bytes | None:
        norm = self._norm_key(key)
        cp = self._cache_path(norm)
        if cp.is_file():
            try:
                os.utime(cp, None)
            except OSError:
                pass
            return cp.read_bytes()

        try:
            resp = self._client.get_object(Bucket=self.bucket, Key=norm)
            data = resp["Body"].read()
            self._write_cache(norm, data)
            return data
        except Exception:  # noqa: BLE001
            return None

    def write_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> None:
        norm = self._norm_key(key)
        self._client.put_object(
            Bucket=self.bucket,
            Key=norm,
            Body=data,
            ContentType=content_type,
        )
        self._write_cache(norm, data)

    def delete_key(self, key: str) -> bool:
        norm = self._norm_key(key)
        cp = self._cache_path(norm)
        if cp.is_file():
            cp.unlink(missing_ok=True)
        try:
            self._client.delete_object(Bucket=self.bucket, Key=norm)
            return True
        except Exception:  # noqa: BLE001
            return False

    def delete_prefix(self, prefix: str) -> int:
        keys = self.list_keys(prefix)
        removed = 0
        for k in keys:
            if self.delete_key(k):
                removed += 1
        return removed

    def list_keys(self, prefix: str) -> list[str]:
        norm_pref = self._norm_key(prefix)
        if norm_pref and not norm_pref.endswith("/"):
            norm_pref = norm_pref + "/"
        keys: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=norm_pref):
            for obj in page.get("Contents", []):
                k = str(obj.get("Key", ""))
                if k and not k.endswith("/"):
                    keys.append(k)
        return sorted(keys)

    def rename_prefix(self, old_prefix: str, new_prefix: str) -> int:
        norm_old = self._norm_key(old_prefix).rstrip("/") + "/"
        norm_new = self._norm_key(new_prefix).rstrip("/") + "/"
        keys = self.list_keys(norm_old)
        moved = 0
        for k in keys:
            if not k.startswith(norm_old):
                continue
            new_k = norm_new + k[len(norm_old) :]
            self._client.copy_object(
                Bucket=self.bucket,
                CopySource={"Bucket": self.bucket, "Key": k},
                Key=new_k,
            )
            self.delete_key(k)
            moved += 1
        return moved


def build_photo_storage(
    settings: Mapping[str, Any],
    base_data_root: Path,
    env: Mapping[str, str] | None = None,
) -> PhotoStorage:
    """Instantiate LocalPhotoStorage or S3PhotoStorage from settings.yaml + environment variables."""
    load_dotenv_if_present()
    environ = os.environ if env is None else env
    st_cfg = settings.get("storage", {}) if isinstance(settings, Mapping) else {}

    backend = (
        environ.get("FW_STORAGE_BACKEND") or str(st_cfg.get("backend", "local"))
    ).strip().lower()

    if backend != "s3":
        return LocalPhotoStorage(base_dir=base_data_root)

    endpoint_url = (
        environ.get("FW_S3_ENDPOINT") or str(st_cfg.get("endpoint_url", ""))
    ).strip()
    region = (environ.get("FW_S3_REGION") or str(st_cfg.get("region", "fsn1"))).strip()
    bucket = (environ.get("FW_S3_BUCKET") or str(st_cfg.get("bucket", ""))).strip()
    ak_env = str(st_cfg.get("access_key_env", "FW_S3_ACCESS_KEY"))
    sk_env = str(st_cfg.get("secret_key_env", "FW_S3_SECRET_KEY"))
    access_key = environ.get(ak_env, environ.get("FW_S3_ACCESS_KEY", "")).strip()
    secret_key = environ.get(sk_env, environ.get("FW_S3_SECRET_KEY", "")).strip()
    cache_mb = int(st_cfg.get("local_cache_max_mb", 500))

    if not bucket or not endpoint_url or not access_key or not secret_key:
        logger.warning(
            "FW_STORAGE_BACKEND=s3 requested but S3 credentials/bucket are incomplete; falling back to LocalPhotoStorage."
        )
        return LocalPhotoStorage(base_dir=base_data_root)

    logger.info(
        "Initialized Hetzner Object Storage backend (bucket=%s, endpoint=%s, cache=%dMB)",
        bucket,
        endpoint_url,
        cache_mb,
    )
    return S3PhotoStorage(
        bucket=bucket,
        endpoint_url=endpoint_url,
        region=region,
        access_key=access_key,
        secret_key=secret_key,
        cache_dir=base_data_root / "_s3_cache",
        local_cache_max_mb=cache_mb,
    )

