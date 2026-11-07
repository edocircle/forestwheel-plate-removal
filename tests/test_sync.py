"""Unit tests for fwphotos.sync (Google Drive rclone sync, readiness check, Telegram alerts)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest
import yaml

from fwphotos.detect import Detection, PlateDetector
from fwphotos.sync import (
    build_rclone_exclude_args,
    is_car_folder_ready,
    send_telegram_alert,
    sync_once,
)


class _SyncStubDetector(PlateDetector):
    """Stub detector for sync tests."""

    def __init__(self) -> None:
        super().__init__(weights_path=Path("models/dummy.pt"), confidence_threshold=0.40)
        self.calls = 0

    def detect_array(
        self, image_bgr: np.ndarray, min_conf: float | None = None
    ) -> list[Detection]:
        self.calls += 1
        marker = int(image_bgr[0, 0, 0])
        if marker == 99:
            raise RuntimeError("Simulated corrupt image decoding failure")
        if marker == 50:
            return []  # no plate -> goes to review
        return [Detection(bbox=(60, 60, 200, 110), confidence=0.92)]


def _write_test_config(tmp_path: Path) -> Path:
    """Create a temporary settings.yaml pointing local sync paths into tmp_path."""
    cfg = {
        "paths": {
            "template_config": "config/template.yaml",
            "plate_overlay_asset": "assets/plate_overlay.png",
            "logo_asset": "assets/logo.png",
        },
        "detection": {
            "weights_path": "models/plate_yolov8n.pt",
            "confidence_threshold": 0.40,
            "max_inference_size": 1280,
            "device": "cpu",
            "supported_extensions": [".jpg", ".jpeg", ".png", ".heic"],
        },
        "overlay": {
            "padding_ratio": 0.08,
            "min_padding_px": 4,
            "feather_px": 5,
        },
        "output": {
            "active_profile": "website",
            "jpeg_quality": 90,
        },
        "sync": {
            "rclone_binary": "rclone",
            "remote_name": "gdrive",
            "remote_inbox": "Forest Wheel Inventory/inbox",
            "remote_processed": "Forest Wheel Inventory/processed",
            "remote_review": "Forest Wheel Inventory/review",
            "local_inbox_dir": str(tmp_path / "inbox"),
            "local_output_dir": str(tmp_path / "output"),
            "local_review_dir": str(tmp_path / "review"),
            "car_state_file": str(tmp_path / "state" / "synced_cars.json"),
            "ready_marker_file": "ready.txt",
            "quiescence_seconds": 90,
            "skip_video_extensions": [".mp4", ".mov"],
            "telegram": {
                "enabled": True,
                "bot_token_env": "FW_TELEGRAM_BOT_TOKEN",
                "chat_id_env": "FW_TELEGRAM_CHAT_ID",
                "timeout_seconds": 5,
            },
        },
    }
    cfg_path = tmp_path / "settings.yaml"
    with cfg_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(cfg, fh)
    return cfg_path


def test_is_car_folder_ready_with_marker_and_quiescence(tmp_path: Path) -> None:
    """is_car_folder_ready checks ready.txt or 90-second file mtime quiescence and ignores videos."""
    exts = [".jpg", ".png"]
    vids = [".mp4", ".mov"]

    # Case 1: Recent file (< 90s old) without ready.txt -> False
    car_a = tmp_path / "car_a"
    car_a.mkdir()
    img_a = car_a / "front.jpg"
    img_a.write_bytes(b"fake-jpg")
    now = 1_700_000_000.0
    os.utime(img_a, (now - 30, now - 30))

    ready, reason = is_car_folder_ready(
        car_a, exts, vids, "ready.txt", quiescence_seconds=90, now_ts=now
    )
    assert not ready
    assert "waiting_for_quiescence" in reason

    # Case 2: Add ready.txt -> immediately True even though file is only 30s old
    (car_a / "ready.txt").write_text("done", encoding="utf-8")
    ready, reason = is_car_folder_ready(
        car_a, exts, vids, "ready.txt", quiescence_seconds=90, now_ts=now
    )
    assert ready
    assert reason == "ready_marker"

    # Case 3: No ready.txt, image is 120s old (>= 90s), even if a brand-new .mp4 video exists -> True
    car_b = tmp_path / "car_b"
    car_b.mkdir()
    img_b = car_b / "rear.png"
    img_b.write_bytes(b"fake-png")
    os.utime(img_b, (now - 120, now - 120))
    vid_b = car_b / "walkaround.mp4"
    vid_b.write_bytes(b"fake-video")
    os.utime(vid_b, (now - 5, now - 5))

    ready, reason = is_car_folder_ready(
        car_b, exts, vids, "ready.txt", quiescence_seconds=90, now_ts=now
    )
    assert ready
    assert "quiescent" in reason


def test_sync_once_full_lifecycle_and_idempotency(tmp_path: Path) -> None:
    """sync_once pulls inbox, processes ready cars, pushes output/review to gdrive, and records state."""
    cfg_path = _write_test_config(tmp_path)
    inbox_dir = tmp_path / "inbox"

    # Car 1: Ready via ready.txt (has 1 good image + 1 no-plate image + 1 ignored .mp4 video)
    car1 = inbox_dir / "SBA1111A"
    car1.mkdir(parents=True)
    img_good = np.full((240, 360, 3), 10, dtype=np.uint8)
    cv2.rectangle(img_good, (60, 60), (200, 110), (245, 245, 245), -1)
    cv2.imwrite(str(car1 / "01_front.png"), img_good)

    img_rev = np.full((240, 360, 3), 50, dtype=np.uint8)
    cv2.imwrite(str(car1 / "02_interior.png"), img_rev)
    (car1 / "video.mp4").write_bytes(b"ignored-video-data")
    (car1 / "ready.txt").write_text("ok", encoding="utf-8")

    # Car 2: Not ready yet (modified 10s ago, no ready.txt)
    car2 = inbox_dir / "SBB2222B"
    car2.mkdir(parents=True)
    cv2.imwrite(str(car2 / "01_front.png"), img_good)
    now = 1_800_000_000.0
    os.utime(car2 / "01_front.png", (now - 10, now - 10))

    rclone_calls: list[list[str]] = []

    def fake_rclone(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        rclone_calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    detector = _SyncStubDetector()
    records = sync_once(
        config_path=cfg_path,
        detector=detector,
        rclone_runner=fake_rclone,
        now_ts=now,
        env={},
    )

    # Only SBA1111A should be processed; SBB2222B is not ready yet
    assert len(records) == 1
    assert records[0].car_id == "SBA1111A"
    assert records[0].output_count == 1
    assert records[0].review_count == 1

    # Verify local output and review folders per car ID
    assert (tmp_path / "output" / "SBA1111A" / "01_front.jpg").exists()
    assert (tmp_path / "review" / "SBA1111A" / "02_interior.png").exists()

    # Verify rclone commands: 1 pull from inbox, 1 push to processed/SBA1111A, 1 push to review/SBA1111A
    assert len(rclone_calls) == 3
    assert "gdrive:Forest Wheel Inventory/inbox" in rclone_calls[0]
    assert "*.mp4" in rclone_calls[0]
    assert "gdrive:Forest Wheel Inventory/processed/SBA1111A" in rclone_calls[1]
    assert "gdrive:Forest Wheel Inventory/review/SBA1111A" in rclone_calls[2]

    # Second cycle: SBA1111A is recorded in synced_cars.json so it is excluded and not reprocessed
    rclone_calls.clear()
    detector_calls_before = detector.calls
    records_second = sync_once(
        config_path=cfg_path,
        detector=detector,
        rclone_runner=fake_rclone,
        now_ts=now + 20,  # still < 90s for SBB2222B
        env={},
    )
    assert len(records_second) == 0
    assert detector.calls == detector_calls_before
    # Verify SBA1111A/** was passed to rclone --exclude on the second inbox pull
    assert "SBA1111A/**" in rclone_calls[0]


def test_telegram_alert_on_rclone_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any rclone error sends a Telegram alert using env vars and raises."""
    cfg_path = _write_test_config(tmp_path)
    sent_requests: list[tuple[str, bytes]] = []

    class _DummyResponse:
        status = 200

        def __enter__(self) -> _DummyResponse:
            return self

        def __exit__(self, *args: Any) -> None:
            pass

    def fake_urlopen(req: Any, timeout: int = 10) -> _DummyResponse:
        sent_requests.append((req.full_url, req.data))
        return _DummyResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    def failing_rclone(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="oauth token expired")

    env = {
        "FW_TELEGRAM_BOT_TOKEN": "123456:TEST_BOT_TOKEN_NOT_REAL",
        "FW_TELEGRAM_CHAT_ID": "-100987654321",
    }

    with pytest.raises(RuntimeError, match="rclone copy failed"):
        sync_once(
            config_path=cfg_path,
            rclone_runner=failing_rclone,
            env=env,
        )

    assert len(sent_requests) == 1
    url, body = sent_requests[0]
    assert "123456:TEST_BOT_TOKEN_NOT_REAL/sendMessage" in url
    assert b"oauth+token+expired" in body or b"oauth%20token%20expired" in body

