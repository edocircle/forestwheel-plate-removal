"""Unit and integration tests for LocalPhotoStorage and Hetzner S3PhotoStorage."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi.testclient import TestClient

from fwphotos.detect import Detection, PlateDetector
from fwphotos.review_app import create_review_app
from fwphotos.storage import LocalPhotoStorage, S3PhotoStorage, build_photo_storage


class _FakeS3Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeS3Paginator:
    def __init__(self, store: dict[str, bytes]) -> None:
        self._store = store

    def paginate(self, Bucket: str, Prefix: str = "") -> list[dict[str, Any]]:
        keys = sorted(k for k in self._store if k.startswith(Prefix))
        return [{"Contents": [{"Key": k} for k in keys]}]


class _FakeS3Client:
    """Minimal in-memory boto3 S3 client stub for testing S3PhotoStorage."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str = "") -> None:
        self.objects[Key] = bytes(Body)

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            raise KeyError(Key)
        return {"Body": _FakeS3Body(self.objects[Key])}

    def head_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        if Key not in self.objects:
            raise KeyError(Key)
        return {"ContentLength": len(self.objects[Key])}

    def delete_object(self, Bucket: str, Key: str) -> None:
        self.objects.pop(Key, None)

    def copy_object(self, Bucket: str, CopySource: dict[str, str], Key: str) -> None:
        src_key = CopySource["Key"]
        if src_key not in self.objects:
            raise KeyError(src_key)
        self.objects[Key] = self.objects[src_key]

    def get_paginator(self, name: str) -> _FakeS3Paginator:
        assert name == "list_objects_v2"
        return _FakeS3Paginator(self.objects)


def test_local_photo_storage_crud(tmp_path: Path) -> None:
    st = LocalPhotoStorage(tmp_path / "store")
    st.write_bytes("accounts/user_1/output/CAR1/01.jpg", b"abc123")
    assert st.exists("accounts/user_1/output/CAR1/01.jpg")
    assert st.read_bytes("accounts/user_1/output/CAR1/01.jpg") == b"abc123"
    assert st.list_keys("accounts/user_1/output") == ["accounts/user_1/output/CAR1/01.jpg"]

    moved = st.rename_prefix("accounts/user_1/output/CAR1", "accounts/user_1/output/CAR2")
    assert moved == 1
    assert not st.exists("accounts/user_1/output/CAR1/01.jpg")
    assert st.exists("accounts/user_1/output/CAR2/01.jpg")

    removed = st.delete_prefix("accounts/user_1/output/CAR2")
    assert removed == 1
    assert not st.exists("accounts/user_1/output/CAR2/01.jpg")


def test_s3_photo_storage_and_lru_cache_eviction(tmp_path: Path) -> None:
    fake_s3 = _FakeS3Client()
    st = S3PhotoStorage(
        bucket="forestwheel-photos-dev",
        endpoint_url="https://fsn1.your-objectstorage.com",
        cache_dir=tmp_path / "cache",
        local_cache_max_mb=1,
        s3_client=fake_s3,
    )
    # Override max_cache_bytes to a tiny 500-byte limit to verify eviction
    st.max_cache_bytes = 500

    st.write_bytes("guest_trial/output/A/1.jpg", b"x" * 350, "image/jpeg")
    st.write_bytes("guest_trial/output/A/2.jpg", b"y" * 350, "image/jpeg")

    # Both exist in S3, while local cache stayed bounded <= 500 bytes
    assert "guest_trial/output/A/1.jpg" in fake_s3.objects
    assert "guest_trial/output/A/2.jpg" in fake_s3.objects
    cached_size = sum(p.stat().st_size for p in (tmp_path / "cache").rglob("*") if p.is_file())
    assert cached_size <= 500

    # Reading evicted key transparently fetches from S3 again
    assert st.read_bytes("guest_trial/output/A/1.jpg") == b"x" * 350


def test_build_photo_storage_env_selection(tmp_path: Path) -> None:
    local_st = build_photo_storage({"storage": {"backend": "local"}}, tmp_path, env={})
    assert local_st.is_s3 is False

    s3_st = build_photo_storage(
        {"storage": {"backend": "local"}},
        tmp_path,
        env={
            "FW_STORAGE_BACKEND": "s3",
            "FW_S3_ENDPOINT": "https://fsn1.your-objectstorage.com",
            "FW_S3_BUCKET": "forestwheel-photos-dev",
            "FW_S3_ACCESS_KEY": "ak",
            "FW_S3_SECRET_KEY": "sk",
        },
    )
    assert s3_st.is_s3 is True


def test_review_app_with_s3_storage_keeps_local_disk_clean(tmp_path: Path) -> None:
    class _HighConfDetector(PlateDetector):
        def __init__(self) -> None:
            super().__init__(weights_path=Path("models/dummy.pt"), confidence_threshold=0.40)

        def detect_array(
            self, image_bgr: np.ndarray, min_conf: float | None = None
        ) -> list[Detection]:
            return [Detection(bbox=(40, 40, 140, 80), confidence=0.95)]

    fake_s3 = _FakeS3Client()
    s3_storage = S3PhotoStorage(
        bucket="forestwheel-photos-dev",
        endpoint_url="https://fsn1.your-objectstorage.com",
        cache_dir=tmp_path / "s3_cache",
        local_cache_max_mb=10,
        s3_client=fake_s3,
    )

    rev_dir = tmp_path / "rev"
    out_dir = tmp_path / "out"
    in_dir = tmp_path / "in"

    app = create_review_app(
        config_path=Path("config/settings.yaml"),
        review_dir_override=rev_dir,
        output_dir_override=out_dir,
        inbox_dir_override=in_dir,
        decisions_file_override=tmp_path / "decisions.json",
        state_file_override=tmp_path / "state.json",
        detector=_HighConfDetector(),
        storage_override=s3_storage,
    )
    client = TestClient(app)

    # Sign up an account so uploads go under accounts/user_1/...
    reg = client.post(
        "/api/profile/register",
        json={"email": "s3dealer@forestwheel.com", "password": "secret", "confirm_password": "secret"},
    )
    assert reg.status_code == 200

    img = np.full((240, 360, 3), (50, 95, 130), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)

    up = client.post(
        "/api/upload",
        data={"car_id": "SGP 7777 Z", "ratio": "1:1", "car_model": "S3 Test Car"},
        files=[("files", ("front.jpg", buf.tobytes(), "image/jpeg"))],
    )
    assert up.status_code == 200
    assert up.json()["output_count"] == 1

    # Verify files are in S3 under accounts/user_1 and NOT stored permanently on local out_dir/in_dir
    assert "accounts/user_1/output/SGP-7777-Z/front.jpg" in fake_s3.objects
    assert "accounts/user_1/inbox/SGP-7777-Z/front.jpg" in fake_s3.objects
    assert not (out_dir / "SGP-7777-Z" / "front.jpg").exists()
    assert not (in_dir / "SGP-7777-Z" / "front.jpg").exists()

    # Verify Gallery state, Before/After media, Frame render, Export ZIP, Rename, and Delete all work via S3
    st = client.get("/api/state").json()
    assert "SGP-7777-Z" in st["cars_output"]

    assert client.get("/media/original/SGP-7777-Z/front.jpg").status_code == 200
    assert client.get("/media/output/SGP-7777-Z/front.jpg").status_code == 200
    assert client.get("/api/frame-render?car_id=SGP-7777-Z&filename=front.jpg&ratio=16:9").status_code == 200
    assert client.get("/api/export/SGP-7777-Z").status_code == 200

    ren = client.put("/api/cars/SGP-7777-Z", json={"new_car_id": "SGP 8888 Z", "car_model": "Renamed S3 Car"})
    assert ren.status_code == 200
    assert "accounts/user_1/output/SGP-8888-Z/front.jpg" in fake_s3.objects
    assert "accounts/user_1/output/SGP-7777-Z/front.jpg" not in fake_s3.objects

    dele = client.post("/api/delete", json={"scope": "car", "car_id": "SGP-8888-Z"})
    assert dele.status_code == 200
    assert "accounts/user_1/output/SGP-8888-Z/front.jpg" not in fake_s3.objects

