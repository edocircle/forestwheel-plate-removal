"""License plate perspective overlay and feather-blending module."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from fwphotos.detect import Detection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OverlayResult:
    """Result of applying plate overlays to an image."""

    image_bgr: np.ndarray
    plates_covered: int
    modes: list[str]  # "perspective" or "fallback" per detection

    @property
    def summary_mode(self) -> str:
        """Return overall overlay mode ('perspective', 'fallback', or 'none')."""
        if not self.modes:
            return "none"
        if "fallback" in self.modes:
            return "fallback"
        return "perspective"


def load_overlay_rgba(asset_path: Path) -> np.ndarray:
    """Load RGBA plate overlay PNG as BGRA numpy array."""
    if not asset_path.exists():
        raise FileNotFoundError(f"Plate overlay asset not found: {asset_path}")
    bgra = cv2.imread(str(asset_path), cv2.IMREAD_UNCHANGED)
    if bgra is None:
        raise ValueError(f"Failed to decode overlay image: {asset_path}")
    if bgra.ndim == 2:
        bgra = cv2.cvtColor(bgra, cv2.COLOR_GRAY2BGRA)
    elif bgra.shape[2] == 3:
        bgra = cv2.cvtColor(bgra, cv2.COLOR_BGR2BGRA)
    return bgra


def order_quad_corners(pts: np.ndarray) -> np.ndarray:
    """Order 4 points consistently as [top-left, top-right, bottom-right, bottom-left]."""
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    # Sort by y first (top 2 vs bottom 2)
    y_sorted = pts[np.argsort(pts[:, 1])]
    top_two = y_sorted[:2]
    bottom_two = y_sorted[2:]

    tl, tr = top_two[np.argsort(top_two[:, 0])]
    bl, br = bottom_two[np.argsort(bottom_two[:, 0])]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def expand_quad(
    quad: np.ndarray,
    pad_ratio: float,
    min_pad_px: int,
    img_width: int,
    img_height: int,
) -> np.ndarray:
    """Expand a 4-point quadrilateral outward from its centroid to ensure full coverage."""
    center = quad.mean(axis=0)
    vecs = quad - center
    dists = np.linalg.norm(vecs, axis=1, keepdims=True)
    safe_dists = np.where(dists > 1e-3, dists, 1.0)
    unit_vecs = vecs / safe_dists

    extra = np.maximum(dists * pad_ratio, float(min_pad_px))
    expanded = center + unit_vecs * (dists + extra)
    expanded[:, 0] = np.clip(expanded[:, 0], 0, img_width - 1)
    expanded[:, 1] = np.clip(expanded[:, 1], 0, img_height - 1)
    return order_quad_corners(expanded)


def padded_bbox_quad(
    bbox: tuple[int, int, int, int],
    pad_ratio: float,
    min_pad_px: int,
    img_width: int,
    img_height: int,
) -> np.ndarray:
    """Return axis-aligned 4-corner quad for a padded bounding box."""
    x1, y1, x2, y2 = bbox
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    pad_x = max(min_pad_px, int(round(bw * pad_ratio)))
    pad_y = max(min_pad_px, int(round(bh * pad_ratio)))

    px1 = max(0, x1 - pad_x)
    py1 = max(0, y1 - pad_y)
    px2 = min(img_width - 1, x2 + pad_x)
    py2 = min(img_height - 1, y2 + pad_y)

    return np.array(
        [[px1, py1], [px2, py1], [px2, py2], [px1, py2]], dtype=np.float32
    )


def estimate_plate_corners(
    image_bgr: np.ndarray,
    bbox: tuple[int, int, int, int],
    overlay_cfg: dict[str, Any],
) -> tuple[np.ndarray, str]:
    """Estimate the 4 corners of a license plate inside bbox.

    Returns (corners_4x2_float32, mode) where mode is 'perspective' or 'fallback'.
    To guarantee no original plate characters remain visible, any detected perspective
    quad must cover the core bounding box area; otherwise we fall back to the
    padded bounding box.
    """
    img_h, img_w = image_bgr.shape[:2]
    pad_ratio = float(overlay_cfg.get("padding_ratio", 0.08))
    min_pad_px = int(overlay_cfg.get("min_padding_px", 4))
    canny_low = int(overlay_cfg.get("canny_low", 50))
    canny_high = int(overlay_cfg.get("canny_high", 150))
    eps_factor = float(overlay_cfg.get("approx_poly_epsilon", 0.04))
    min_area_ratio = float(overlay_cfg.get("min_quad_area_ratio", 0.25))
    max_area_ratio = float(overlay_cfg.get("max_quad_area_ratio", 0.98))

    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    if bw < 12 or bh < 8:
        return padded_bbox_quad(bbox, pad_ratio, min_pad_px, img_w, img_h), "fallback"

    crop_pad_x = max(min_pad_px, int(round(bw * pad_ratio)))
    crop_pad_y = max(min_pad_px, int(round(bh * pad_ratio)))
    cx1 = max(0, x1 - crop_pad_x)
    cy1 = max(0, y1 - crop_pad_y)
    cx2 = min(img_w, x2 + crop_pad_x)
    cy2 = min(img_h, y2 + crop_pad_y)

    crop = image_bgr[cy1:cy2, cx1:cx2]
    crop_h, crop_w = crop.shape[:2]
    crop_area = float(crop_h * crop_w)
    if crop_area <= 0:
        return padded_bbox_quad(bbox, pad_ratio, min_pad_px, img_w, img_h), "fallback"

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, canny_low, canny_high)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    candidate_quad: np.ndarray | None = None
    for cnt in contours[:10]:
        area = cv2.contourArea(cnt)
        if area < crop_area * min_area_ratio or area > crop_area * max_area_ratio:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, eps_factor * peri, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            candidate_quad = approx.reshape(4, 2).astype(np.float32)
            break

        rect = cv2.minAreaRect(cnt)
        box_pts = cv2.boxPoints(rect)
        rect_area = cv2.contourArea(box_pts)
        if crop_area * min_area_ratio <= rect_area <= crop_area * max_area_ratio:
            candidate_quad = box_pts.astype(np.float32)
            break

    if candidate_quad is None:
        return padded_bbox_quad(bbox, pad_ratio, min_pad_px, img_w, img_h), "fallback"

    # Translate from crop coordinates to full image coordinates
    full_quad = order_quad_corners(candidate_quad + np.array([cx1, cy1], dtype=np.float32))
    expanded_quad = expand_quad(full_quad, pad_ratio, min_pad_px, img_w, img_h)

    # Verify geometry sanity: width > height and covers core plate region
    top_w = float(np.linalg.norm(expanded_quad[1] - expanded_quad[0]))
    bot_w = float(np.linalg.norm(expanded_quad[2] - expanded_quad[3]))
    left_h = float(np.linalg.norm(expanded_quad[3] - expanded_quad[0]))
    right_h = float(np.linalg.norm(expanded_quad[2] - expanded_quad[1]))

    if min(top_w, bot_w) < bw * 0.75 or min(left_h, right_h) < bh * 0.65:
        return padded_bbox_quad(bbox, pad_ratio, min_pad_px, img_w, img_h), "fallback"

    return expanded_quad, "perspective"


def warp_and_composite_single(
    canvas_bgr: np.ndarray,
    overlay_bgra: np.ndarray,
    dst_quad: np.ndarray,
    feather_px: int = 5,
) -> np.ndarray:
    """Warp overlay_bgra onto dst_quad using perspective transform and feather edges."""
    img_h, img_w = canvas_bgr.shape[:2]
    ov_h, ov_w = overlay_bgra.shape[:2]

    src_quad = np.array(
        [[0, 0], [ov_w - 1, 0], [ov_w - 1, ov_h - 1], [0, ov_h - 1]],
        dtype=np.float32,
    )
    dst_pts = order_quad_corners(dst_quad)

    # Compute ROI bounding box around dst_pts to avoid warping across a full 4K frame
    min_x = max(0, int(np.floor(dst_pts[:, 0].min())) - feather_px - 2)
    min_y = max(0, int(np.floor(dst_pts[:, 1].min())) - feather_px - 2)
    max_x = min(img_w, int(np.ceil(dst_pts[:, 0].max())) + feather_px + 2)
    max_y = min(img_h, int(np.ceil(dst_pts[:, 1].max())) + feather_px + 2)

    roi_w = max_x - min_x
    roi_h = max_y - min_y
    if roi_w <= 1 or roi_h <= 1:
        raise ValueError("Invalid destination quadrilateral for overlay warp.")

    local_dst = dst_pts - np.array([min_x, min_y], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src_quad, local_dst)

    warped_bgra = cv2.warpPerspective(
        overlay_bgra,
        matrix,
        (roi_w, roi_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )

    # Build polygon mask and feather only the outer boundary while keeping interior 100% opaque
    poly_mask = np.zeros((roi_h, roi_w), dtype=np.uint8)
    cv2.fillConvexPoly(poly_mask, np.round(local_dst).astype(np.int32), 255)

    alpha = (warped_bgra[:, :, 3].astype(np.float32) / 255.0) * (
        poly_mask.astype(np.float32) / 255.0
    )

    if feather_px > 0:
        ksize = int(feather_px) * 2 + 1
        blurred_alpha = cv2.GaussianBlur(alpha, (ksize, ksize), 0)
        # Erode polygon slightly so the core plate region stays 1.0 opaque
        erode_k = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (max(3, feather_px), max(3, feather_px))
        )
        core_mask = cv2.erode(poly_mask, erode_k, iterations=1)
        alpha = np.where(core_mask > 0, alpha, blurred_alpha)

    alpha_3c = np.clip(alpha[:, :, None], 0.0, 1.0)
    roi_bgr = canvas_bgr[min_y:max_y, min_x:max_x].astype(np.float32)
    warped_bgr = warped_bgra[:, :, :3].astype(np.float32)

    blended_roi = warped_bgr * alpha_3c + roi_bgr * (1.0 - alpha_3c)
    result = canvas_bgr.copy()
    result[min_y:max_y, min_x:max_x] = np.clip(blended_roi, 0, 255).astype(np.uint8)
    return result


def apply_plate_overlays(
    image_bgr: np.ndarray,
    detections: list[Detection],
    settings: dict[str, Any],
    overlay_bgra: np.ndarray | None = None,
) -> OverlayResult:
    """Apply branded plate overlay to all detected plates in image_bgr."""
    if not detections:
        return OverlayResult(
            image_bgr=image_bgr.copy(), plates_covered=0, modes=[]
        )

    paths_cfg = settings.get("paths", {})
    overlay_cfg = settings.get("overlay", {})
    feather_px = int(overlay_cfg.get("feather_px", 5))
    pad_ratio = float(overlay_cfg.get("padding_ratio", 0.08))
    min_pad_px = int(overlay_cfg.get("min_padding_px", 4))

    if overlay_bgra is None:
        asset_path = Path(
            paths_cfg.get("plate_overlay_asset", "assets/plate_overlay.png")
        )
        overlay_bgra = load_overlay_rgba(asset_path)

    canvas = image_bgr.copy()
    img_h, img_w = canvas.shape[:2]
    modes: list[str] = []

    for det in detections:
        try:
            quad, mode = estimate_plate_corners(canvas, det.bbox, overlay_cfg)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Corner estimation error (%s); using fallback bbox.", exc)
            quad = padded_bbox_quad(det.bbox, pad_ratio, min_pad_px, img_w, img_h)
            mode = "fallback"

        canvas = warp_and_composite_single(
            canvas, overlay_bgra, quad, feather_px=feather_px
        )
        modes.append(mode)

    return OverlayResult(
        image_bgr=canvas,
        plates_covered=len(modes),
        modes=modes,
    )
