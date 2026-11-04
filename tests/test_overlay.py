"""Unit tests for fwphotos.overlay module."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from fwphotos.detect import Detection, load_settings
from fwphotos.overlay import (
    apply_plate_overlays,
    estimate_plate_corners,
    order_quad_corners,
)


def _make_angled_plate_image() -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Create a synthetic car bumper image with a bright angled rectangle plate."""
    img = np.full((400, 600, 3), (45, 45, 50), dtype=np.uint8)
    quad = np.array(
        [[180, 170], [420, 190], [415, 255], [175, 235]], dtype=np.int32
    )
    cv2.fillConvexPoly(img, quad, (245, 245, 245))
    cv2.polylines(img, [quad], True, (10, 10, 10), 3)
    # Draw simulated pure blue characters inside plate (not present in green/gold/white overlay)
    cv2.rectangle(img, (210, 195), (390, 230), (255, 0, 0), -1)
    bbox = (175, 170, 420, 255)
    return img, bbox


def test_order_quad_corners() -> None:
    """order_quad_corners orders points as [TL, TR, BR, BL] regardless of input order."""
    scrambled = np.array([[400, 250], [100, 120], [410, 130], [95, 240]], dtype=np.float32)
    ordered = order_quad_corners(scrambled)
    assert tuple(ordered[0]) == (100.0, 120.0)  # TL
    assert tuple(ordered[1]) == (410.0, 130.0)  # TR
    assert tuple(ordered[2]) == (400.0, 250.0)  # BR
    assert tuple(ordered[3]) == (95.0, 240.0)   # BL


def test_perspective_corner_estimation_and_full_coverage() -> None:
    """Angled high-contrast plate uses 'perspective' mode and completely hides plate interior."""
    img, bbox = _make_angled_plate_image()
    settings = load_settings(Path("config/settings.yaml"))

    quad, mode = estimate_plate_corners(img, bbox, settings["overlay"])
    assert mode == "perspective"
    assert quad.shape == (4, 2)

    result = apply_plate_overlays(
        img, [Detection(bbox=bbox, confidence=0.92)], settings
    )
    assert result.plates_covered == 1
    assert result.summary_mode == "perspective"

    # Original image unchanged
    assert (img[210, 300] == np.array([255, 0, 0])).all()
    # Verify 0 pixels of the original blue characters or bright white plate remain visible
    roi_after = result.image_bgr[170:260, 175:425]
    blue_char_pixels = np.sum(
        (roi_after[:, :, 0] > 200) & (roi_after[:, :, 1] < 30) & (roi_after[:, :, 2] < 30)
    )
    assert int(blue_char_pixels) == 0


def test_fallback_when_no_quad_edges_exist() -> None:
    """Uniform textureless crop triggers 'fallback' mode and still covers the bounding box."""
    img = np.full((300, 500, 3), (120, 120, 120), dtype=np.uint8)
    bbox = (150, 100, 350, 160)
    settings = load_settings(Path("config/settings.yaml"))

    result = apply_plate_overlays(
        img, [Detection(bbox=bbox, confidence=0.85)], settings
    )
    assert result.plates_covered == 1
    assert result.summary_mode == "fallback"
    # Verify center pixel changed from uniform gray (120, 120, 120)
    assert not np.array_equal(result.image_bgr[130, 250], np.array([120, 120, 120]))
