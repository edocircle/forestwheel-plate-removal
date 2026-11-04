"""Unit tests for the Phase 5 FastAPI review web application."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from fwphotos.detect import Detection, PlateDetector
from fwphotos.review_app import create_review_app


class _ReviewStubDetector(PlateDetector):
    """Stub detector for review web app tests."""

    def __init__(self) -> None:
        super().__init__(weights_path=Path("models/dummy.pt"), confidence_threshold=0.40)

    def detect_array(
        self, image_bgr: np.ndarray, min_conf: float | None = None
    ) -> list[Detection]:
        return [Detection(bbox=(40, 40, 140, 80), confidence=0.35)]


def _setup_review_fixture(tmp_path: Path) -> tuple[TestClient, Path, Path, Path]:
    """Create a test review/ and output/ hierarchy with two cars in review/."""
    review_dir = tmp_path / "review"
    output_dir = tmp_path / "output"
    decisions_file = tmp_path / "review_decisions.json"
    state_file = tmp_path / "processed_state.json"

    car_dir = review_dir / "SBA8888X"
    car_dir.mkdir(parents=True)

    img1 = np.full((200, 300, 3), (60, 90, 140), dtype=np.uint8)
    cv2.imwrite(str(car_dir / "01_rear_angle.jpg"), img1)
    cv2.imwrite(str(car_dir / "02_interior.jpg"), img1)

    state_file.write_text(
        json.dumps(
            {
                "01_rear_angle.jpg": {"reason": "low_confidence (0.3500 < 0.4000)"},
                "02_interior.jpg": {"reason": "no_plate_detected"},
            }
        ),
        encoding="utf-8",
    )

    env = {
        "FW_REVIEW_USER": "reviewer",
        "FW_REVIEW_PASS": "s3cr3t-pass",
    }

    app = create_review_app(
        config_path=Path("config/settings.yaml"),
        review_dir_override=review_dir,
        output_dir_override=output_dir,
        decisions_file_override=decisions_file,
        state_file_override=state_file,
        detector=_ReviewStubDetector(),
        env=env,
    )
    return TestClient(app), review_dir, output_dir, decisions_file


def test_unauthenticated_requests_never_expose_photos(tmp_path: Path) -> None:
    """Every HTML, API, and media endpoint rejects unauthenticated or wrong-password requests."""
    client, _, _, _ = _setup_review_fixture(tmp_path)

    endpoints = [
        ("GET", "/"),
        ("GET", "/api/items"),
        ("GET", "/media/before/SBA8888X/01_rear_angle.jpg"),
        ("GET", "/media/after/SBA8888X/01_rear_angle.jpg"),
        ("POST", "/api/approve/SBA8888X/01_rear_angle.jpg"),
        ("POST", "/api/reject/SBA8888X/02_interior.jpg"),
    ]
    for method, url in endpoints:
        # No credentials
        resp_no_auth = client.request(method, url)
        assert resp_no_auth.status_code == 401
        assert "Basic" in resp_no_auth.headers.get("WWW-Authenticate", "")

        # Wrong password
        resp_bad_auth = client.request(method, url, auth=("reviewer", "wrong"))
        assert resp_bad_auth.status_code == 401


def test_authenticated_dashboard_and_before_after_thumbnails(tmp_path: Path) -> None:
    """Authenticated user sees car cards, logged reasons, and valid JPEG before/after thumbnails."""
    client, _, _, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    resp = client.get("/", auth=auth)
    assert resp.status_code == 200
    assert "SBA8888X" in resp.text
    assert "01_rear_angle.jpg" in resp.text
    assert "low_confidence (0.3500 &lt; 0.4000)" in resp.text
    assert "no_plate_detected" in resp.text

    before_resp = client.get("/media/before/SBA8888X/01_rear_angle.jpg", auth=auth)
    assert before_resp.status_code == 200
    assert before_resp.headers["content-type"] == "image/jpeg"
    assert before_resp.content[:2] == b"\xff\xd8"  # JPEG magic bytes

    after_resp = client.get("/media/after/SBA8888X/01_rear_angle.jpg", auth=auth)
    assert after_resp.status_code == 200
    assert after_resp.headers["content-type"] == "image/jpeg"
    assert after_resp.content[:2] == b"\xff\xd8"


def test_approve_moves_to_output_and_reject_marks_rejected_in_review(
    tmp_path: Path,
) -> None:
    """Approve writes composed image to output/ and removes from review/; Reject keeps in review/ marked rejected."""
    client, review_dir, output_dir, decisions_file = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # 1. Approve 01_rear_angle.jpg
    app_resp = client.post("/api/approve/SBA8888X/01_rear_angle.jpg", auth=auth)
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "approved"

    # File moved from review/SBA8888X/01_rear_angle.jpg -> output/SBA8888X/01_rear_angle.jpg
    assert not (review_dir / "SBA8888X" / "01_rear_angle.jpg").exists()
    assert (output_dir / "SBA8888X" / "01_rear_angle.jpg").exists()

    # 2. Reject 02_interior.jpg
    rej_resp = client.post("/api/reject/SBA8888X/02_interior.jpg", auth=auth)
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "rejected"

    # File stays in review/ and is marked rejected in decisions JSON and UI
    assert (review_dir / "SBA8888X" / "02_interior.jpg").exists()
    decisions = json.loads(decisions_file.read_text(encoding="utf-8"))
    assert decisions["SBA8888X/02_interior.jpg"]["status"] == "rejected"

    items_resp = client.get("/api/items", auth=auth).json()
    remaining = items_resp["cars"]["SBA8888X"]
    assert len(remaining) == 1
    assert remaining[0]["filename"] == "02_interior.jpg"
    assert remaining[0]["status"] == "rejected"
