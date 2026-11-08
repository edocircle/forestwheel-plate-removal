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


def test_steep_three_quarter_tilted_plate_follows_tilt_angle() -> None:
    """A steeply tilted 3/4-angle plate (where top-right corner is lower than bottom-left) preserves its tilt slope."""
    img = np.full((420, 640, 3), (40, 42, 46), dtype=np.uint8)
    # Steeply tilted plate: left side around y=160..210, right side around y=225..275
    # Note that TR.y (225) > BL.y (210), which previously broke y-first corner sorting!
    tilted_quad = np.array(
        [[180, 160], [430, 225], [420, 275], [170, 210]], dtype=np.int32
    )
    cv2.fillConvexPoly(img, tilted_quad, (240, 240, 240))
    cv2.polylines(img, [tilted_quad], True, (15, 15, 15), 2)

    bbox = (170, 160, 430, 275)
    settings = load_settings(Path("config/settings.yaml"))

    est_quad, mode = estimate_plate_corners(img, bbox, settings["overlay"])
    assert mode == "perspective"
    # Top-right corner must be significantly lower (larger y) than top-left corner, matching the tilt
    tl, tr, br, bl = est_quad
    assert (tr[1] - tl[1]) > 35.0
    assert (br[1] - bl[1]) > 35.0


def test_dark_plate_with_collinear_characters_estimates_tidy_parallel_quad() -> None:
    """Dark plate on a dark bumper (no visible plate border) estimates a tidy parallel quad from character blobs."""
    from fwphotos.detect import count_collinear_plate_blobs

    # Dark bumper and dark plate background (nearly identical luminance so contour thresholding merges them)
    img = np.full((420, 640, 3), (28, 28, 30), dtype=np.uint8)
    # Draw 6 angled white character-sized blocks along a 12-degree tilted line
    for i in range(6):
        cx = 200 + i * 32
        cy = int(190 + i * 6.5)
        cv2.rectangle(img, (cx - 8, cy - 16), (cx + 8, cy + 16), (235, 235, 235), -1)

    bbox = (175, 160, 405, 255)
    assert count_collinear_plate_blobs(img, bbox) >= 5

    # Uniform textureless interior region has 0 collinear blobs
    assert count_collinear_plate_blobs(img, (10, 10, 150, 80)) == 0

    settings = load_settings(Path("config/settings.yaml"))
    est_quad, mode = estimate_plate_corners(img, bbox, settings["overlay"])
    assert mode == "perspective"
    tl, tr, br, bl = est_quad
    left_h = float(np.linalg.norm(bl - tl))
    right_h = float(np.linalg.norm(br - tr))
    # Left and right edge heights must be balanced (tidy parallel quad, not a wedge)
    assert min(left_h, right_h) / max(left_h, right_h) >= 0.85
    # Must follow the downward-right tilt of the characters
    assert (tr[1] - tl[1]) > 20.0


def test_high_dpi_apple_frame_studio_and_crisp_logo_badge(tmp_path: Path) -> None:
    """render_apple_frame_studio outputs 2160x2160 for 1:1 and trims transparent logo margins for high-res badge."""
    from PIL import Image
    from fwphotos.compose import render_apple_frame_studio

    sample_bgr = np.full((800, 1200, 3), (90, 110, 130), dtype=np.uint8)
    # Create a 1200x1200 RGBA logo with large transparent margins and a bright red center emblem
    logo_rgba = Image.new("RGBA", (1200, 1200), (0, 0, 0, 0))
    emblem = Image.new("RGBA", (600, 600), (220, 20, 40, 255))
    logo_rgba.paste(emblem, (300, 300))
    logo_file = tmp_path / "logo_padded.png"
    logo_rgba.save(logo_file, format="PNG")

    framed = render_apple_frame_studio(
        sample_bgr,
        ratio="1:1",
        fit_mode="fit",
        template_style="clean_white",
        logo_path=logo_file,
        show_logo_watermark=True,
    )
    assert framed.size == (2160, 2160)
    # Top-right badge zone should contain a substantial area of crisp red emblem pixels
    arr = np.array(framed)
    top_right = arr[0:380, 1700:2160]
    red_pixels = int(np.sum((top_right[:, :, 0] > 180) & (top_right[:, :, 1] < 60)))
    assert red_pixels > 8000


