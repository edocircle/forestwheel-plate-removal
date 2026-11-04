"""Unit tests for fwphotos.compose and fwphotos.pipeline modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest
from PIL import Image

from fwphotos.compose import compose_template, load_template_config
from fwphotos.detect import Detection, PlateDetector
from fwphotos.pipeline import run_pipeline


class _StubDetector(PlateDetector):
    """Deterministic stub detector mapping filename substrings to detections."""

    def __init__(self, mapping: dict[str, list[Detection]]) -> None:
        super().__init__(weights_path=Path("models/dummy.pt"), confidence_threshold=0.40)
        self._mapping = mapping
        self.call_count = 0

    def detect_array(
        self, image_bgr: np.ndarray, min_conf: float | None = None
    ) -> list[Detection]:
        self.call_count += 1
        # Identify image by top-left pixel marker
        marker = int(image_bgr[0, 0, 0])
        dets = self._mapping.get(str(marker), [])
        thresh = self.confidence_threshold if min_conf is None else min_conf
        return [d for d in dets if d.confidence >= thresh]


def test_compose_template_website_and_social_profiles() -> None:
    """compose_template produces exact canvas dimensions for both website and social_4_5."""
    template_cfg = load_template_config(Path("config/template.yaml"))
    sample_bgr = np.full((600, 800, 3), (80, 120, 160), dtype=np.uint8)

    web_img = compose_template(sample_bgr, template_cfg, profile_name="website")
    assert isinstance(web_img, Image.Image)
    assert web_img.size == (1600, 1200)

    social_img = compose_template(sample_bgr, template_cfg, profile_name="social_4_5")
    assert social_img.size == (1080, 1350)

    with pytest.raises(KeyError):
        compose_template(sample_bgr, template_cfg, profile_name="nonexistent")


def test_pipeline_failsafe_and_idempotency(tmp_path: Path) -> None:
    """Pipeline routes valid plates to output/, missing/low-conf to review/, and skips on re-run."""
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    rev_dir = tmp_path / "review"
    state_file = tmp_path / "state.json"
    in_dir.mkdir()

    # 1. Valid plate image (marker=10)
    img_good = np.full((300, 400, 3), 10, dtype=np.uint8)
    cv2.rectangle(img_good, (120, 120), (280, 170), (245, 245, 245), -1)
    cv2.imwrite(str(in_dir / "car_good.jpg"), img_good)

    # 2. Low confidence plate image (marker=20)
    img_low = np.full((300, 400, 3), 20, dtype=np.uint8)
    cv2.imwrite(str(in_dir / "car_low_conf.png"), img_low)

    # 3. No plate image (marker=30)
    img_none = np.full((300, 400, 3), 30, dtype=np.uint8)
    cv2.imwrite(str(in_dir / "car_no_plate.png"), img_none)

    # Note: PNG is lossless so pixel [0,0,0] stays exact; re-save car_good as PNG too
    (in_dir / "car_good.jpg").unlink()
    cv2.imwrite(str(in_dir / "car_good.png"), img_good)

    stub = _StubDetector(
        mapping={
            "10": [Detection(bbox=(120, 120, 280, 170), confidence=0.91)],
            "20": [Detection(bbox=(100, 100, 200, 140), confidence=0.22)],
            "30": [],
        }
    )

    records_first = run_pipeline(
        input_dir=in_dir,
        output_dir=out_dir,
        review_dir=rev_dir,
        state_file=state_file,
        detector=stub,
    )

    assert len(records_first) == 3
    by_name = {r.filename: r for r in records_first}

    assert by_name["car_good.png"].destination == "output"
    assert by_name["car_good.png"].reason == "ok"
    assert (out_dir / "car_good.jpg").exists()

    assert by_name["car_low_conf.png"].destination == "review"
    assert "low_confidence" in by_name["car_low_conf.png"].reason
    assert (rev_dir / "car_low_conf.png").exists()

    assert by_name["car_no_plate.png"].destination == "review"
    assert by_name["car_no_plate.png"].reason == "no_plate_detected"
    assert (rev_dir / "car_no_plate.png").exists()

    # Re-run: idempotency must skip all 3 images without invoking detector again
    calls_before = stub.call_count
    records_second = run_pipeline(
        input_dir=in_dir,
        output_dir=out_dir,
        review_dir=rev_dir,
        state_file=state_file,
        detector=stub,
    )
    assert len(records_second) == 3
    assert stub.call_count == calls_before
