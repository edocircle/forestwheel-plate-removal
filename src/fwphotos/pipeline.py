"""End-to-end photo processing pipeline with fail-safe routing and idempotency."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fwphotos.compose import compose_template, load_template_config
from fwphotos.detect import (
    Detection,
    PlateDetector,
    list_supported_images,
    load_image_bgr,
    load_settings,
)
from fwphotos.overlay import apply_plate_overlays, load_overlay_rgba

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImageProcessRecord:
    """Audit record for a single processed image."""

    filename: str
    file_hash: str
    plates_found: int
    max_confidence: float
    overlay_mode: str
    destination: str  # "output" or "review"
    output_path: str
    reason: str


def compute_file_hash(file_path: Path, profile_name: str) -> str:
    """Compute SHA-256 digest of file contents + active template profile for idempotency."""
    hasher = hashlib.sha256()
    hasher.update(profile_name.encode("utf-8"))
    with file_path.open("rb") as fh:
        while chunk := fh.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_state(state_file: Path) -> dict[str, dict[str, Any]]:
    """Load processed image state dictionary from JSON file."""
    if not state_file.exists():
        return {}
    try:
        with state_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read state file %s (%s); starting fresh.", state_file, exc)
        return {}


def save_state(state_file: Path, state: dict[str, dict[str, Any]]) -> None:
    """Persist processed image state dictionary to JSON file."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)


def _route_to_review(
    img_path: Path,
    review_dir: Path,
    file_hash: str,
    plates_found: int,
    max_conf: float,
    overlay_mode: str,
    reason: str,
) -> ImageProcessRecord:
    """Copy original image untouched to review_dir and log structured reason."""
    review_dir.mkdir(parents=True, exist_ok=True)
    dest_file = review_dir / img_path.name
    shutil.copy2(img_path, dest_file)

    record = ImageProcessRecord(
        filename=img_path.name,
        file_hash=file_hash,
        plates_found=plates_found,
        max_confidence=round(max_conf, 4),
        overlay_mode=overlay_mode,
        destination="review",
        output_path=str(dest_file),
        reason=reason,
    )
    logger.warning(
        "filename=%s | plates_found=%d | confidence=%.4f | overlay_mode=%s | destination=review | reason=%s",
        record.filename,
        record.plates_found,
        record.max_confidence,
        record.overlay_mode,
        record.reason,
    )
    return record


def process_single_image(
    img_path: Path,
    output_dir: Path,
    review_dir: Path,
    detector: PlateDetector,
    settings: dict[str, Any],
    template_cfg: dict[str, Any],
    overlay_bgra: Any,
    profile_name: str,
    file_hash: str,
) -> ImageProcessRecord:
    """Process one image with strict 'no plate, no publish' fail-safe routing."""
    threshold = float(
        settings.get("detection", {}).get("confidence_threshold", 0.40)
    )
    jpeg_quality = int(settings.get("output", {}).get("jpeg_quality", 92))

    try:
        image_bgr = load_image_bgr(img_path)
        # Run detection with a low floor (0.05) so we can distinguish "no_plate_detected"
        # vs "low_confidence" (< threshold) in the review reason log.
        raw_detections: list[Detection] = detector.detect_array(
            image_bgr, min_conf=min(0.05, threshold)
        )
    except Exception as exc:  # noqa: BLE001
        return _route_to_review(
            img_path=img_path,
            review_dir=review_dir,
            file_hash=file_hash,
            plates_found=0,
            max_conf=0.0,
            overlay_mode="none",
            reason=f"detection_error: {exc}",
        )

    if not raw_detections:
        return _route_to_review(
            img_path=img_path,
            review_dir=review_dir,
            file_hash=file_hash,
            plates_found=0,
            max_conf=0.0,
            overlay_mode="none",
            reason="no_plate_detected",
        )

    max_raw_conf = max(d.confidence for d in raw_detections)
    valid_detections = [d for d in raw_detections if d.confidence >= threshold]

    if not valid_detections:
        return _route_to_review(
            img_path=img_path,
            review_dir=review_dir,
            file_hash=file_hash,
            plates_found=0,
            max_conf=max_raw_conf,
            overlay_mode="none",
            reason=f"low_confidence ({max_raw_conf:.4f} < {threshold:.4f})",
        )

    try:
        overlay_res = apply_plate_overlays(
            image_bgr=image_bgr,
            detections=valid_detections,
            settings=settings,
            overlay_bgra=overlay_bgra,
        )
        if overlay_res.plates_covered < len(valid_detections) or overlay_res.plates_covered < 1:
            raise RuntimeError("Overlay did not cover all detected plates.")

        composed_pil = compose_template(
            image_bgr=overlay_res.image_bgr,
            template_cfg=template_cfg,
            profile_name=profile_name,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / f"{img_path.stem}.jpg"
        composed_pil.save(out_file, format="JPEG", quality=jpeg_quality)
    except Exception as exc:  # noqa: BLE001
        return _route_to_review(
            img_path=img_path,
            review_dir=review_dir,
            file_hash=file_hash,
            plates_found=len(valid_detections),
            max_conf=max_raw_conf,
            overlay_mode="none",
            reason=f"processing_error: {exc}",
        )

    record = ImageProcessRecord(
        filename=img_path.name,
        file_hash=file_hash,
        plates_found=overlay_res.plates_covered,
        max_confidence=round(max_raw_conf, 4),
        overlay_mode=overlay_res.summary_mode,
        destination="output",
        output_path=str(out_file),
        reason="ok",
    )
    logger.info(
        "filename=%s | plates_found=%d | confidence=%.4f | overlay_mode=%s | destination=output | reason=ok",
        record.filename,
        record.plates_found,
        record.max_confidence,
        record.overlay_mode,
    )
    return record


def run_pipeline(
    input_dir: Path,
    output_dir: Path,
    review_dir: Path,
    config_path: Path = Path("config/settings.yaml"),
    state_file: Path | None = None,
    profile: str | None = None,
    force: bool = False,
    detector: PlateDetector | None = None,
) -> list[ImageProcessRecord]:
    """Run the full detect -> overlay -> compose pipeline on input_dir."""
    settings = load_settings(config_path)
    paths_cfg = settings.get("paths", {})
    det_cfg = settings.get("detection", {})
    out_cfg = settings.get("output", {})

    template_path = Path(paths_cfg.get("template_config", "config/template.yaml"))
    template_cfg = load_template_config(template_path)
    profile_name = profile or str(out_cfg.get("active_profile", "website"))

    if state_file is None:
        state_file = Path(paths_cfg.get("state_file", "data/processed_state.json"))

    if detector is None:
        detector = PlateDetector.from_config(settings)

    overlay_asset_path = Path(
        paths_cfg.get("plate_overlay_asset", "assets/plate_overlay.png")
    )
    overlay_bgra = (
        load_overlay_rgba(overlay_asset_path)
        if overlay_asset_path.exists()
        else None
    )

    extensions = det_cfg.get(
        "supported_extensions", [".jpg", ".jpeg", ".png", ".heic"]
    )
    image_paths = list_supported_images(input_dir, extensions)
    state = load_state(state_file)
    records: list[ImageProcessRecord] = []

    for img_path in image_paths:
        try:
            file_hash = compute_file_hash(img_path, profile_name)
        except Exception as exc:  # noqa: BLE001
            rec = _route_to_review(
                img_path=img_path,
                review_dir=review_dir,
                file_hash="",
                plates_found=0,
                max_conf=0.0,
                overlay_mode="none",
                reason=f"hash_error: {exc}",
            )
            records.append(rec)
            continue

        existing = state.get(img_path.name)
        if (
            not force
            and existing
            and existing.get("file_hash") == file_hash
            and Path(existing.get("output_path", "")).exists()
        ):
            logger.info(
                "filename=%s | skipped (already processed to %s)",
                img_path.name,
                existing.get("destination"),
            )
            records.append(ImageProcessRecord(**existing))
            continue

        record = process_single_image(
            img_path=img_path,
            output_dir=output_dir,
            review_dir=review_dir,
            detector=detector,
            settings=settings,
            template_cfg=template_cfg,
            overlay_bgra=overlay_bgra,
            profile_name=profile_name,
            file_hash=file_hash,
        )
        state[img_path.name] = asdict(record)
        save_state(state_file, state)
        records.append(record)

    return records
