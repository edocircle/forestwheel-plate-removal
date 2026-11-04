"""Unit tests for fwphotos.detect module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest
from PIL import Image
from pillow_heif import register_heif_opener

from fwphotos.detect import (
    Detection,
    PlateDetector,
    load_image_bgr,
    resize_for_inference,
    save_debug_image,
    scale_bbox_to_original,
)

register_heif_opener()


@dataclass
class _DummyTensor:
    data: np.ndarray

    def cpu(self) -> _DummyTensor:
        return self

    def numpy(self) -> np.ndarray:
        return self.data


class _DummyBoxes:
    def __init__(self, xyxy: list[list[float]], conf: list[float]) -> None:
        self.xyxy = _DummyTensor(np.array(xyxy, dtype=np.float32))
        self.conf = _DummyTensor(np.array(conf, dtype=np.float32))


class _DummyResult:
    def __init__(self, boxes: _DummyBoxes) -> None:
        self.boxes = boxes


class _DummyModel:
    def __init__(self, xyxy: list[list[float]], conf: list[float]) -> None:
        self._xyxy = xyxy
        self._conf = conf
        self.last_input_shape: tuple[int, ...] | None = None

    def predict(
        self, source: np.ndarray, conf: float, device: str, verbose: bool
    ) -> list[_DummyResult]:
        self.last_input_shape = source.shape
        return [_DummyResult(_DummyBoxes(self._xyxy, self._conf))]


def test_resize_and_scale_bbox_back_to_original() -> None:
    """Large images are downscaled for inference and bounding boxes scale back accurately."""
    orig_h, orig_w = 2400, 3600
    large_img = np.zeros((orig_h, orig_w, 3), dtype=np.uint8)
    resized, scale = resize_for_inference(large_img, max_dim=1200)

    assert resized.shape[1] == 1200
    assert resized.shape[0] == 800
    assert pytest.approx(scale, rel=1e-4) == 1200 / 3600

    # Box in resized image (300, 400, 600, 500) -> should map to (900, 1200, 1800, 1500)
    scaled = scale_bbox_to_original((300.0, 400.0, 600.0, 500.0), scale, orig_w, orig_h)
    assert scaled == (900, 1200, 1800, 1500)


def test_detector_scales_coordinates_and_filters_confidence() -> None:
    """PlateDetector resizes large input, filters by confidence, and returns original coordinates."""
    dummy_model = _DummyModel(
        xyxy=[[100.0, 200.0, 300.0, 250.0], [50.0, 50.0, 120.0, 80.0]],
        conf=[0.88, 0.25],
    )
    detector = PlateDetector(
        weights_path=Path("models/dummy.pt"),
        confidence_threshold=0.40,
        max_inference_size=1000,
        model=dummy_model,
    )

    # 2000x1000 image -> resized to 1000x500 (scale = 0.5)
    img = np.zeros((1000, 2000, 3), dtype=np.uint8)
    detections = detector.detect_array(img)

    assert dummy_model.last_input_shape == (500, 1000, 3)
    assert len(detections) == 1
    assert detections[0].bbox == (200, 400, 600, 500)
    assert pytest.approx(detections[0].confidence, rel=1e-3) == 0.88


def test_load_image_formats_jpg_png_heic(tmp_path: Path) -> None:
    """load_image_bgr supports JPEG, PNG, and HEIC formats."""
    fixtures_dir = Path("tests/fixtures")
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    rgb = np.full((64, 96, 3), (40, 120, 200), dtype=np.uint8)
    pil_img = Image.fromarray(rgb)

    jpg_path = fixtures_dir / "sample_car.jpg"
    png_path = fixtures_dir / "sample_car.png"
    heic_path = tmp_path / "sample_car.heic"

    pil_img.save(jpg_path, format="JPEG", quality=95)
    pil_img.save(png_path, format="PNG")
    pil_img.save(heic_path, format="HEIF")

    for path in (jpg_path, png_path, heic_path):
        loaded = load_image_bgr(path)
        assert loaded.shape == (64, 96, 3)


def test_save_debug_image(tmp_path: Path) -> None:
    """save_debug_image writes an annotated image without modifying original array."""
    orig = np.zeros((120, 200, 3), dtype=np.uint8)
    dets = [Detection(bbox=(20, 30, 100, 60), confidence=0.91)]
    out_file = tmp_path / "debug_out.jpg"

    save_debug_image(orig, dets, out_file)
    assert out_file.exists()
    assert int(orig.sum()) == 0  # original untouched
    saved = cv2.imread(str(out_file))
    assert saved is not None
    assert int(saved.sum()) > 0
