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
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            xyxy_list = boxes.xyxy.cpu().numpy().tolist()
            conf_list = boxes.conf.cpu().numpy().tolist()
            for coords, conf in zip(xyxy_list, conf_list):
                if float(conf) < threshold:
                    continue
                scaled_box = scale_bbox_to_original(
                    (coords[0], coords[1], coords[2], coords[3]),
                    scale,
                    orig_w,
                    orig_h,
                )
                detections.append(
                    Detection(bbox=scaled_box, confidence=round(float(conf), 4))
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

