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
    """Order 4 points consistently as [top-left, top-right, bottom-right, bottom-left].

    Works reliably even on steeply tilted 3/4-angle vehicle shots by splitting
    left-two vs right-two points along X (since license plates are wider than tall)
    and then ordering top vs bottom within each side.
    """
    pts = np.asarray(pts, dtype=np.float32).reshape(4, 2)
    x_sorted = pts[np.argsort(pts[:, 0])]
    left_two = x_sorted[:2]
    right_two = x_sorted[2:]

    tl, bl = left_two[np.argsort(left_two[:, 1])]
    tr, br = right_two[np.argsort(right_two[:, 1])]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def _fit_quad_from_hull(hull_pts: np.ndarray) -> np.ndarray:
    """Fit a 4-corner perspective quadrilateral to a convex hull of edge/plate points.

    Uses directional extreme points (TL, TR, BR, BL) along rotated axes aligned
    with the minimum-area bounding rectangle so angled plates preserve both their
    tilt angle and perspective foreshortening.
    """
    rect = cv2.minAreaRect(hull_pts)
    box = order_quad_corners(cv2.boxPoints(rect))
    pts = hull_pts.reshape(-1, 2).astype(np.float32)
    if len(pts) < 4:
        return box

    # Primary axis along the top/bottom edges of the minAreaRect
    u_vec = box[1] - box[0]
    u_len = float(np.linalg.norm(u_vec))
    if u_len < 1e-3:
        return box
    u_unit = u_vec / u_len
    v_unit = np.array([-u_unit[1], u_unit[0]], dtype=np.float32)

    center = pts.mean(axis=0)
    rel = pts - center
    u_proj = rel @ u_unit
    v_proj = rel @ v_unit

    # Normalize projections so X and Y contribute equally to corner extremeness
    u_span = max(1.0, float(u_proj.max() - u_proj.min()))
    v_span = max(1.0, float(v_proj.max() - v_proj.min()))
    u_norm = u_proj / u_span
    v_norm = v_proj / v_span

    tl = pts[int(np.argmin(u_norm + v_norm))]
    tr = pts[int(np.argmax(u_norm - v_norm))]
    br = pts[int(np.argmax(u_norm + v_norm))]
    bl = pts[int(np.argmin(u_norm - v_norm))]
    fitted = order_quad_corners(np.array([tl, tr, br, bl], dtype=np.float32))

    # Blend 65% perspective-hull extremes with 35% minAreaRect to stabilize noisy corners
    # while keeping the true tilt angle and perspective taper of the plate.
    return order_quad_corners(0.65 * fitted + 0.35 * box)


def _estimate_slant_quad_from_gradients(
    gray: np.ndarray,
    core_x1: int,
    core_y1: int,
    core_x2: int,
    core_y2: int,
) -> np.ndarray | None:
    """Estimate a tilted parallelogram/trapezoid from horizontal plate edges and character baseline."""
    roi = gray[core_y1:core_y2, core_x1:core_x2]
    rh, rw = roi.shape[:2]
    if rh < 8 or rw < 16:
        return None

    # Compute vertical gradient |dI/dy| which is strong along top/bottom plate borders and characters
    gy = cv2.Sobel(roi, cv2.CV_32F, 0, 1, ksize=3)
    abs_gy = np.abs(gy)
    thresh = float(np.percentile(abs_gy, 82))
    if thresh < 8.0:
        return None

    ys, xs = np.where(abs_gy >= thresh)
    if len(xs) < 16:
        return None

    # Fit a line y = slope * x + intercept to the strong horizontal structure of the plate
    vx, vy, x0, y0 = cv2.fitLine(
        np.column_stack([xs, ys]).astype(np.float32),
        cv2.DIST_L1,
        0,
        0.01,
        0.01,
    )
    vx_f = float(vx[0]) if np.ndim(vx) > 0 else float(vx)
    vy_f = float(vy[0]) if np.ndim(vy) > 0 else float(vy)
    if abs(vx_f) < 1e-3:
        return None

    slope = vy_f / vx_f
    # Clamp to realistic license plate camera tilt (up to ~35 degrees)
    slope = float(np.clip(slope, -0.70, 0.70))
    if abs(slope) < 0.015:
        return None

    # For each column slice, find the top and bottom vertical bounds along that tilted line
    residuals = ys.astype(np.float32) - slope * (xs.astype(np.float32) - rw * 0.5)
    top_res = float(np.percentile(residuals, 4))
    bot_res = float(np.percentile(residuals, 96))
    plate_thickness = max(rh * 0.55, bot_res - top_res)
    mid_res = 0.5 * (top_res + bot_res)

    half_t = 0.52 * plate_thickness
    dy_left = slope * (0.0 - rw * 0.5)
    dy_right = slope * (rw - rw * 0.5)

    tl = [core_x1 + 0.0, core_y1 + mid_res + dy_left - half_t]
    tr = [core_x1 + float(rw), core_y1 + mid_res + dy_right - half_t]
    br = [core_x1 + float(rw), core_y1 + mid_res + dy_right + half_t]
    bl = [core_x1 + 0.0, core_y1 + mid_res + dy_left + half_t]
    return order_quad_corners(np.array([tl, tr, br, bl], dtype=np.float32))


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


def _estimate_quad_from_character_line(
    image_bgr: np.ndarray,
    bbox: tuple[int, int, int, int],
    pad_ratio: float,
    min_pad_px: int,
) -> np.ndarray | None:
    """Fit a parallel perspective quadrilateral directly to collinear plate character blobs via RANSAC.

    Prevents bumper shadows, grille slats, or sub-frames from distorting the plate cover into
    a wedge or shrinking it to a partial sliver.
    """
    img_h, img_w = image_bgr.shape[:2]
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    if bw < 28 or bh < 12:
        return None

    roi = cv2.cvtColor(image_bgr[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(roi, (3, 3), 0)

    best_inliers: list[tuple[float, float, float, float, float]] = []
    best_score = -1.0

    for inv in (False, True):
        src = (255 - blur) if inv else blur
        kw = max(15, int(round(bw * 0.14)) | 1)
        kh = max(11, int(round(bh * 0.45)) | 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
        tophat = cv2.morphologyEx(src, cv2.MORPH_TOPHAT, kernel)
        _, th = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        num_l, _, stats, centroids = cv2.connectedComponentsWithStats(th)
        cands: list[tuple[float, float, float, float, float]] = []
        for i in range(1, num_l):
            _, _, cw, ch, area = stats[i]
            if (bw * 0.012) <= cw <= (bw * 0.26) and (bh * 0.12) <= ch <= (bh * 0.88):
                aspect = ch / max(1.0, float(cw))
                if 0.6 <= aspect <= 7.5 and area >= max(12, int(bw * bh * 0.0008)):
                    cands.append(
                        (
                            float(centroids[i][0]),
                            float(centroids[i][1]),
                            float(cw),
                            float(ch),
                            float(area),
                        )
                    )

        n = len(cands)
        if n < 4:
            continue
        for i in range(n):
            for j in range(i + 1, n):
                xi, yi, _, hi, _ = cands[i]
                xj, yj, _, hj, _ = cands[j]
                dx = xj - xi
                if abs(dx) < bw * 0.14:
                    continue
                if not (0.68 <= (hi / max(1.0, hj)) <= 1.47):
                    continue
                m = (yj - yi) / dx
                if abs(m) > 0.78:
                    continue
                b = yi - m * xi
                y_mid = m * (bw * 0.5) + b
                if not (bh * 0.18 <= y_mid <= bh * 0.82):
                    continue
                ref_h = 0.5 * (hi + hj)
                inliers = [
                    c
                    for c in cands
                    if 0.65 <= (c[3] / ref_h) <= 1.50
                    and abs(c[1] - (m * c[0] + b)) <= max(ref_h * 0.35, bh * 0.08)
                ]
                if len(inliers) >= 4:
                    xs_in = [c[0] for c in inliers]
                    span = (max(xs_in) - min(xs_in)) / max(1.0, float(bw))
                    score = len(inliers) * (0.4 + span)
                    if score > best_score and span >= 0.34:
                        best_score = score
                        best_inliers = inliers

    if len(best_inliers) < 4:
        return None

    xs = np.array([c[0] for c in best_inliers], dtype=np.float32)
    ys = np.array([c[1] for c in best_inliers], dtype=np.float32)
    hs = np.array([c[3] for c in best_inliers], dtype=np.float32)
    m_fit, b_fit = np.polyfit(xs, ys, 1)
    slope = float(np.clip(m_fit, -0.75, 0.75))
    char_h = float(np.percentile(hs, 75))
    aspect = bw / max(1.0, float(bh))

    if aspect >= 2.9 and abs(slope) < 0.08:
        abs_dy = min(abs(slope) * bw, bh * 0.22)
        half_t = 0.5 * (bh - abs_dy)
        y_left = 0.5 * bh - 0.5 * (slope * bw)
        y_right = 0.5 * bh + 0.5 * (slope * bw)
    else:
        half_t = float(np.clip(char_h * 0.90, bh * 0.25, bh * 0.44))
        y_left = float(np.clip(slope * 0.0 + b_fit, half_t, bh - half_t))
        y_right = float(np.clip(slope * float(bw) + b_fit, half_t, bh - half_t))

    tl = [x1, y1 + y_left - half_t]
    tr = [x2, y1 + y_right - half_t]
    br = [x2, y1 + y_right + half_t]
    bl = [x1, y1 + y_left + half_t]
    quad = np.array([tl, tr, br, bl], dtype=np.float32)
    return expand_quad(quad, pad_ratio, min_pad_px, img_w, img_h)


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

    # First try RANSAC collinear character-line perspective quad (handles real angled & straight plates cleanly)
    char_quad = _estimate_quad_from_character_line(
        image_bgr, bbox, pad_ratio, min_pad_px
    )
    if char_quad is not None:
        return char_quad, "perspective"

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

    # Multi-pass candidate extraction:
    # 1) Canny edge closing
    # 2) Adaptive local threshold (captures dark/light plate frames & character rows)
    # 3) Otsu bright/dark plate region threshold
    edges = cv2.Canny(blurred, canny_low, canny_high)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    adapt = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 4
    )
    closed_adapt = cv2.morphologyEx(adapt, cv2.MORPH_CLOSE, kernel, iterations=2)

    _, otsu_bright = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, otsu_dark = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    candidate_quad: np.ndarray | None = None

    for binary_map in (closed_edges, otsu_bright, otsu_dark, closed_adapt):
        contours, _ = cv2.findContours(
            binary_map, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for cnt in contours[:12]:
            hull = cv2.convexHull(cnt)
            area = cv2.contourArea(hull)
            if area < crop_area * min_area_ratio or area > crop_area * max_area_ratio:
                continue

            peri = cv2.arcLength(hull, True)
            for eps in (eps_factor, 0.03, 0.06, 0.09):
                approx = cv2.approxPolyDP(hull, eps * peri, True)
                if len(approx) == 4 and cv2.isContourConvex(approx):
                    candidate_quad = approx.reshape(4, 2).astype(np.float32)
                    break
            if candidate_quad is not None:
                break

            # Fit directional 4-corner perspective quad from convex hull
            rect = cv2.minAreaRect(hull)
            box_pts = cv2.boxPoints(rect)
            rect_area = cv2.contourArea(box_pts)
            if crop_area * min_area_ratio <= rect_area <= crop_area * max_area_ratio:
                candidate_quad = _fit_quad_from_hull(hull)
                break
        if candidate_quad is not None:
            break

    # If single-contour extraction didn't find a valid quad, try gradient-based slant estimation
    # inside the core bbox (catches angled plates where the outer plate frame blends with the bumper)
    if candidate_quad is None:
        core_x1 = x1 - cx1
        core_y1 = y1 - cy1
        core_x2 = x2 - cx1
        core_y2 = y2 - cy1
        slant_quad = _estimate_slant_quad_from_gradients(
            blurred, core_x1, core_y1, core_x2, core_y2
        )
        if slant_quad is not None:
            candidate_quad = slant_quad

    if candidate_quad is None:
        return padded_bbox_quad(bbox, pad_ratio, min_pad_px, img_w, img_h), "fallback"

    # Translate from crop coordinates to full image coordinates
    full_quad = order_quad_corners(candidate_quad + np.array([cx1, cy1], dtype=np.float32))
    expanded_quad = expand_quad(full_quad, pad_ratio, min_pad_px, img_w, img_h)

    # Verify geometry sanity: spans the plate width and height even when tilted at 3/4 car angles
    top_w = float(np.linalg.norm(expanded_quad[1] - expanded_quad[0]))
    bot_w = float(np.linalg.norm(expanded_quad[2] - expanded_quad[3]))
    left_h = float(np.linalg.norm(expanded_quad[3] - expanded_quad[0]))
    right_h = float(np.linalg.norm(expanded_quad[2] - expanded_quad[1]))
    x_span = float(expanded_quad[:, 0].max() - expanded_quad[:, 0].min())
    y_span = float(expanded_quad[:, 1].max() - expanded_quad[:, 1].min())

    if (
        min(top_w, bot_w) < bw * 0.65
        or x_span < bw * 0.72
        or max(left_h, right_h, y_span) < bh * 0.45
        or min(left_h, right_h) / max(1.0, max(left_h, right_h)) < 0.68
    ):
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

