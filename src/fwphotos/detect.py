"""License plate detection module using Ultralytics YOLO on CPU."""

from __future__ import annotations

import logging
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Detection:
    """Single license plate detection in original image coordinates."""

    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    confidence: float


def load_settings(config_path: Path = Path("config/settings.yaml")) -> dict[str, Any]:
    """Load YAML configuration settings from disk."""
    with config_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_image_bgr(image_path: Path) -> np.ndarray:
    """Load JPEG, PNG, or HEIC image with EXIF orientation applied as BGR numpy array."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    with Image.open(image_path) as pil_img:
        transposed = ImageOps.exif_transpose(pil_img)
        rgb_img = transposed.convert("RGB")
        rgb_arr = np.asarray(rgb_img, dtype=np.uint8)
    return cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)


def resize_for_inference(
    image_bgr: np.ndarray, max_dim: int
) -> tuple[np.ndarray, float]:
    """Resize image if its longest side exceeds max_dim; return (resized_img, scale)."""
    height, width = image_bgr.shape[:2]
    longest = max(height, width)
    if longest <= max_dim or max_dim <= 0:
        return image_bgr, 1.0

    scale = max_dim / float(longest)
    new_w = max(1, int(round(width * scale)))
    new_h = max(1, int(round(height * scale)))
    resized = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


def scale_bbox_to_original(
    bbox: tuple[float, float, float, float],
    scale: float,
    orig_width: int,
    orig_height: int,
) -> tuple[int, int, int, int]:
    """Scale bounding box from resized inference coordinates back to original image bounds."""
    x1, y1, x2, y2 = bbox
    inv_scale = 1.0 / scale if scale > 0 else 1.0
    ox1 = max(0, min(orig_width - 1, int(round(x1 * inv_scale))))
    oy1 = max(0, min(orig_height - 1, int(round(y1 * inv_scale))))
    ox2 = max(ox1 + 1, min(orig_width, int(round(x2 * inv_scale))))
    oy2 = max(oy1 + 1, min(orig_height, int(round(y2 * inv_scale))))
    return (ox1, oy1, ox2, oy2)


def count_collinear_plate_blobs(
    image_bgr: np.ndarray, bbox: tuple[int, int, int, int]
) -> int:
    """Count collinear character-sized connected components inside bbox (without OCR).

    Used to verify that medium-confidence YOLO candidates actually contain a row of
    license-plate character strokes rather than interior dashboard switches, grilles,
    or door sill trim.
    """
    x1, y1, x2, y2 = bbox
    bw, bh = x2 - x1, y2 - y1
    if bw < 20 or bh < 8:
        return 0

    roi_bgr = image_bgr[y1:y2, x1:x2]
    if roi_bgr.size == 0:
        return 0
    roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    if float(np.std(roi)) < 12.0:
        return 0

    scale = 200.0 / max(1, bw)
    nh = max(28, int(round(bh * scale)))
    norm = cv2.resize(roi, (200, nh), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(norm, (3, 3), 0)

    best = 0
    for inv in (False, True):
        src = (255 - blur) if inv else blur
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, max(11, nh // 2)))
        tophat = cv2.morphologyEx(src, cv2.MORPH_TOPHAT, kernel)
        _, th = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        num_l, _, stats, centroids = cv2.connectedComponentsWithStats(th)
        cands: list[tuple[float, float, int]] = []
        for i in range(1, num_l):
            _, _, cw, ch, area = stats[i]
            if 3 <= cw <= 52 and (nh * 0.11) <= ch <= (nh * 0.88) and area >= 16:
                aspect = ch / max(1.0, float(cw))
                if 0.6 <= aspect <= 7.0:
                    cands.append((float(centroids[i][0]), float(centroids[i][1]), int(ch)))

        if len(cands) >= 4:
            xs = np.array([c[0] for c in cands], dtype=np.float32)
            ys = np.array([c[1] for c in cands], dtype=np.float32)
            hs = np.array([c[2] for c in cands], dtype=np.float32)
            m, b = np.polyfit(xs, ys, 1)
            res = np.abs(ys - (m * xs + b))
            med_h = float(np.median(hs))
            inliers = (res <= nh * 0.20) & (hs >= med_h * 0.55) & (hs <= med_h * 1.8)
            xs_in = xs[inliers]
            if len(xs_in) >= 4 and float(xs_in.max() - xs_in.min()) >= 60.0:
                best = max(best, int(len(xs_in)))
            else:
                best = max(best, int(np.sum(inliers)))
        else:
            best = max(best, len(cands))
    return best


def ensure_weights(weights_path: Path, weights_url: str | None = None) -> Path:
    """Ensure YOLO model weights exist locally; download from weights_url if missing."""
    if weights_path.exists():
        return weights_path
    if not weights_url:
        raise FileNotFoundError(
            f"Model weights not found at {weights_path} and no weights_url configured."
        )
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading pretrained plate detection weights to %s ...", weights_path)
    req = urllib.request.Request(
        weights_url, headers={"User-Agent": "ForestWheel-Pipeline/0.1"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp, weights_path.open("wb") as out:
        out.write(resp.read())
    logger.info("Downloaded weights (%d bytes).", weights_path.stat().st_size)
    return weights_path


class PlateDetector:
    """Lazy-loaded CPU YOLO license plate detector."""

    def __init__(
        self,
        weights_path: Path,
        weights_url: str | None = None,
        confidence_threshold: float = 0.40,
        max_inference_size: int = 1280,
        device: str = "cpu",
        model: Any | None = None,
    ) -> None:
        self.weights_path = Path(weights_path)
        self.weights_url = weights_url
        self.confidence_threshold = float(confidence_threshold)
        self.max_inference_size = int(max_inference_size)
        self.device = device
        self._model = model

    @classmethod
    def from_config(cls, settings: dict[str, Any]) -> PlateDetector:
        """Instantiate PlateDetector from settings dictionary."""
        det_cfg = settings.get("detection", {})
        return cls(
            weights_path=Path(det_cfg.get("weights_path", "models/plate_yolov8n.pt")),
            weights_url=det_cfg.get("weights_url"),
            confidence_threshold=float(det_cfg.get("confidence_threshold", 0.40)),
            max_inference_size=int(det_cfg.get("max_inference_size", 1280)),
            device=str(det_cfg.get("device", "cpu")),
        )

    def _get_model(self) -> Any:
        """Load the Ultralytics YOLO model on first use."""
        if self._model is None:
            from ultralytics import YOLO

            resolved = ensure_weights(self.weights_path, self.weights_url)
            self._model = YOLO(str(resolved))
        return self._model

    def detect_array(
        self, image_bgr: np.ndarray, min_conf: float | None = None
    ) -> list[Detection]:
        """Run plate detection on an in-memory BGR image and return scaled detections."""
        orig_h, orig_w = image_bgr.shape[:2]
        resized_bgr, scale = resize_for_inference(image_bgr, self.max_inference_size)

        threshold = self.confidence_threshold if min_conf is None else min_conf
        model = self._get_model()
        results = model.predict(
            source=resized_bgr,
            conf=threshold,
            device=self.device,
            verbose=False,
        )

        detections: list[Detection] = []
        is_textured_photo = float(np.std(resized_bgr)) >= 12.0

        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            xyxy_list = boxes.xyxy.cpu().numpy().tolist()
            conf_list = boxes.conf.cpu().numpy().tolist()
            for coords, conf in zip(xyxy_list, conf_list):
                conf_f = float(conf)
                if conf_f < threshold:
                    continue
                scaled_box = scale_bbox_to_original(
                    (coords[0], coords[1], coords[2], coords[3]),
                    scale,
                    orig_w,
                    orig_h,
                )
                # Filter out medium-confidence false positives on non-plate car parts
                # (steering wheel switches, door sills, engine covers, mirrors)
                if is_textured_photo and conf_f < 0.70:
                    blobs = count_collinear_plate_blobs(image_bgr, scaled_box)
                    if blobs < 4:
                        continue

                detections.append(
                    Detection(bbox=scaled_box, confidence=round(conf_f, 4))
                )

        # Rescue angled Singapore black-background white-character plates where standard
        # white-plate YOLO confidence was below threshold, verified by inverted luminance + >=5 character blobs
        if not detections and is_textured_photo and threshold >= 0.35:
            gray_res = cv2.cvtColor(resized_bgr, cv2.COLOR_BGR2GRAY)
            inv_res = cv2.cvtColor(255 - gray_res, cv2.COLOR_GRAY2BGR)
            inv_results = model.predict(
                source=inv_res,
                conf=max(threshold, 0.50),
                device=self.device,
                verbose=False,
            )
            for result in inv_results:
                boxes = getattr(result, "boxes", None)
                if boxes is None:
                    continue
                xyxy_list = boxes.xyxy.cpu().numpy().tolist()
                conf_list = boxes.conf.cpu().numpy().tolist()
                for coords, conf in zip(xyxy_list, conf_list):
                    conf_f = float(conf)
                    if conf_f < max(threshold, 0.50):
                        continue
                    scaled_box = scale_bbox_to_original(
                        (coords[0], coords[1], coords[2], coords[3]),
                        scale,
                        orig_w,
                        orig_h,
                    )
                    bx1, by1, bx2, by2 = scaled_box
                    # Must not touch outer frame border and must have >= 5 collinear plate blobs
                    if bx1 <= 8 or by1 <= 8 or bx2 >= orig_w - 8 or by2 >= orig_h - 8:
                        continue
                    if (bx2 - bx1) > orig_w * 0.36:
                        continue
                    if count_collinear_plate_blobs(image_bgr, scaled_box) >= 5:
                        detections.append(
                            Detection(bbox=scaled_box, confidence=round(conf_f, 4))
                        )

        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections

    def detect_image(
        self, image_path: Path, min_conf: float | None = None
    ) -> list[Detection]:
        """Load an image from disk and return license plate detections."""
        image_bgr = load_image_bgr(Path(image_path))
        return self.detect_array(image_bgr, min_conf=min_conf)


def detect_plates(
    image_path: Path | str,
    config_path: Path = Path("config/settings.yaml"),
    detector: PlateDetector | None = None,
) -> list[Detection]:
    """Convenience function: given an image path, return list of plate detections."""
    if detector is None:
        settings = load_settings(config_path)
        detector = PlateDetector.from_config(settings)
    return detector.detect_image(Path(image_path))


def save_debug_image(
    image_bgr: np.ndarray,
    detections: list[Detection],
    output_path: Path,
) -> Path:
    """Draw detected plate bounding boxes and confidence scores (never plate text) and save."""
    annotated = image_bgr.copy()
    for det in detections:
        x1, y1, x2, y2 = det.bbox
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 3)
        label = f"plate {det.confidence:.2f}"
        label_y = max(20, y1 - 8)
        cv2.putText(
            annotated,
            label,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), annotated)
    return output_path


def list_supported_images(input_dir: Path, extensions: list[str]) -> list[Path]:
    """Return sorted list of image files in input_dir matching supported extensions."""
    ext_set = {ext.lower() for ext in extensions}
    if not input_dir.exists():
        return []
    files = [
        p
        for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in ext_set
    ]
    return sorted(files, key=lambda p: p.name.lower())

