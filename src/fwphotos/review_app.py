"""FastAPI web application for Forest Wheel Plate Removal System (Stitch UI/UX aligned).

Supports:
- Mandatory HTTP Basic Auth on every route (never exposes photos unauthenticated).
- Multi-file upload per Car ID with automatic YOLOv8 plate detection, perspective overlay,
  and template cropping into 1:1, 16:9, or 9:16 ratios.
- Vehicle Galleries with live 1:1 / 16:9 / 9:16 ratio switching and single/ZIP batch export.
- Interactive Split-Screen Plate Review UI with 4-corner perspective warp calibration,
  Approve (moves to output/), and Reject (leaves in review/ marked rejected).
- Template Studio live preview for 1:1, 16:9, and 9:16 ratios.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import secrets
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from PIL import Image

from fwphotos.compose import compose_template, load_template_config
from fwphotos.detect import (
    PlateDetector,
    list_supported_images,
    load_image_bgr,
    load_settings,
)
from fwphotos.overlay import (
    apply_plate_overlays,
    load_overlay_rgba,
    warp_and_composite_single,
)
from fwphotos.pipeline import run_pipeline
from fwphotos.ui_template import STITCH_UI_HTML

logger = logging.getLogger(__name__)
security = HTTPBasic(auto_error=False)

RATIO_TO_PROFILE: dict[str, str] = {
    "1:1": "ratio_1_1",
    "ratio_1_1": "ratio_1_1",
    "16:9": "ratio_16_9",
    "ratio_16_9": "ratio_16_9",
    "9:16": "ratio_9_16",
    "ratio_9_16": "ratio_9_16",
    "4:3": "website",
    "website": "website",
    "4:5": "social_4_5",
    "social_4_5": "social_4_5",
}


def resolve_ratio_profile(ratio: str | None, default_profile: str = "ratio_16_9") -> str:
    """Map user-facing aspect ratio ('1:1', '16:9', '9:16') to template.yaml profile name."""
    if not ratio:
        return default_profile
    return RATIO_TO_PROFILE.get(ratio.strip().lower(), default_profile)


def _load_json_dict(path: Path) -> dict[str, Any]:
    """Read a JSON dictionary from disk if it exists."""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed reading JSON %s: %s", path, exc)
        return {}


def _save_json_dict(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON dictionary to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)


def _sanitize_car_id(raw_car_id: str) -> str:
    """Sanitize a user-supplied car ID slug to alphanumeric, hyphen, and underscore."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", raw_car_id.strip()).strip("-")
    return cleaned or "FW-BATCH"


def _validate_path_segment(segment: str) -> str:
    """Prevent directory traversal in car_id or filename parameters."""
    if (
        not segment
        or "/" in segment
        or "\\" in segment
        or ".." in segment
        or segment.startswith(".")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path segment."
        )
    return segment


def _resolve_child_file(base_dir: Path, car_id: str, filename: str) -> Path:
    """Resolve and verify a file inside base_dir/<car_id>/<filename> or base_dir/<filename>."""
    safe_car = _validate_path_segment(car_id)
    safe_name = _validate_path_segment(filename)

    if safe_car == "_root":
        candidate = (base_dir / safe_name).resolve()
    else:
        candidate = (base_dir / safe_car / safe_name).resolve()

    base_resolved = base_dir.resolve()
    if base_resolved not in candidate.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path."
        )
    if not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found."
        )
    return candidate


def _lookup_logged_reason(
    car_id: str,
    filename: str,
    state_file: Path,
    car_state_dir: Path | None,
) -> str:
    """Look up the logged review reason from pipeline state files."""
    if car_id != "_root" and car_state_dir is not None:
        car_img_state = _load_json_dict(car_state_dir / f"images_{car_id}.json")
        if filename in car_img_state:
            return str(car_img_state[filename].get("reason", "manual_review"))

    global_state = _load_json_dict(state_file)
    if filename in global_state:
        return str(global_state[filename].get("reason", "manual_review"))

    return "manual_review"


def _render_composed_image(
    img_path: Path,
    settings: dict[str, Any],
    template_cfg: dict[str, Any],
    detector: PlateDetector,
    overlay_bgra: Any,
    profile_name: str,
    low_conf_floor: float = 0.05,
    custom_quad_pct: list[list[float]] | None = None,
) -> Image.Image:
    """Generate the 'After' composed image for a given template ratio profile."""
    image_bgr = load_image_bgr(img_path)
    img_h, img_w = image_bgr.shape[:2]

    if custom_quad_pct and len(custom_quad_pct) == 4 and overlay_bgra is not None:
        pts = np.array(
            [[p[0] * img_w / 100.0, p[1] * img_h / 100.0] for p in custom_quad_pct],
            dtype=np.float32,
        )
        feather_px = int(settings.get("overlay", {}).get("feather_px", 5))
        processed_bgr = warp_and_composite_single(
            image_bgr, overlay_bgra, pts, feather_px=feather_px
        )
    else:
        detections = detector.detect_array(image_bgr, min_conf=low_conf_floor)
        if detections:
            ov_res = apply_plate_overlays(
                image_bgr=image_bgr,
                detections=detections,
                settings=settings,
                overlay_bgra=overlay_bgra,
            )
            processed_bgr = ov_res.image_bgr
        else:
            processed_bgr = image_bgr

    return compose_template(processed_bgr, template_cfg, profile_name=profile_name)


def _pil_to_jpeg_bytes(pil_img: Image.Image, max_width: int = 0, quality: int = 90) -> bytes:
    """Optionally resize PIL image and encode as JPEG bytes."""
    img = pil_img.convert("RGB")
    if max_width > 0 and img.width > max_width:
        ratio = max_width / float(img.width)
        new_h = max(1, int(round(img.height * ratio)))
        img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def create_review_app(
    config_path: Path = Path("config/settings.yaml"),
    review_dir_override: Path | None = None,
    output_dir_override: Path | None = None,
    inbox_dir_override: Path | None = None,
    decisions_file_override: Path | None = None,
    state_file_override: Path | None = None,
    detector: PlateDetector | None = None,
    env: dict[str, str] | None = None,
) -> FastAPI:
    """Create and configure the Stitch-aligned FastAPI application."""
    settings = load_settings(config_path)
    paths_cfg = settings.get("paths", {})
    det_cfg = settings.get("detection", {})
    sync_cfg = settings.get("sync", {})
    app_cfg = settings.get("review_app", {})

    review_dir = Path(
        review_dir_override or paths_cfg.get("review_dir", "data/review")
    )
    output_dir = Path(
        output_dir_override or paths_cfg.get("output_dir", "data/output")
    )
    inbox_dir = Path(inbox_dir_override or Path("data/inbox"))
    decisions_file = Path(
        decisions_file_override
        or app_cfg.get("decisions_file", "data/review_decisions.json")
    )
    state_file = Path(
        state_file_override or paths_cfg.get("state_file", "data/processed_state.json")
    )
    car_state_file_cfg = sync_cfg.get("car_state_file")
    car_state_dir = Path(car_state_file_cfg).parent if car_state_file_cfg else state_file.parent

    template_path = Path(paths_cfg.get("template_config", "config/template.yaml"))
    template_cfg = load_template_config(template_path)

    overlay_path = Path(
        paths_cfg.get("plate_overlay_asset", "assets/plate_overlay.png")
    )
    overlay_bgra = load_overlay_rgba(overlay_path) if overlay_path.exists() else None

    supported_exts = list(
        det_cfg.get("supported_extensions", [".jpg", ".jpeg", ".png", ".heic"])
    )
    thumb_width = int(app_cfg.get("thumbnail_width", 800))
    low_conf_floor = float(app_cfg.get("low_conf_preview_floor", 0.05))
    jpeg_quality = int(settings.get("output", {}).get("jpeg_quality", 92))

    user_env_key = str(app_cfg.get("auth_user_env", "FW_REVIEW_USER"))
    pass_env_key = str(app_cfg.get("auth_pass_env", "FW_REVIEW_PASS"))

    detector_instance = detector

    def _get_detector() -> PlateDetector:
        nonlocal detector_instance
        if detector_instance is None:
            detector_instance = PlateDetector.from_config(settings)
        return detector_instance

    def verify_auth(
        credentials: HTTPBasicCredentials | None = Depends(security),
    ) -> str:
        """Enforce HTTP Basic Auth on every endpoint; never expose photos unauthenticated."""
        environ = os.environ if env is None else env
        expected_user = environ.get(user_env_key, "")
        expected_pass = environ.get(pass_env_key, "")

        if not expected_user or not expected_pass:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Review authentication credentials are not configured.",
                headers={"WWW-Authenticate": 'Basic realm="Forest Wheel Review"'},
            )
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": 'Basic realm="Forest Wheel Review"'},
            )

        user_ok = secrets.compare_digest(
            credentials.username.encode("utf-8"), expected_user.encode("utf-8")
        )
        pass_ok = secrets.compare_digest(
            credentials.password.encode("utf-8"), expected_pass.encode("utf-8")
        )
        if not (user_ok and pass_ok):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"WWW-Authenticate": 'Basic realm="Forest Wheel Review"'},
            )
        return credentials.username

    app = FastAPI(
        title="Forest Wheel Plate Removal System",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    def _discover_folder_tree(base_folder: Path, is_review: bool = False) -> dict[str, list[dict[str, Any]]]:
        """Group images inside base_folder by car_id (or '_root' for flat files)."""
        decisions = _load_json_dict(decisions_file) if is_review else {}
        grouped: dict[str, list[dict[str, Any]]] = {}
        if not base_folder.exists():
            return grouped

        root_imgs = list_supported_images(base_folder, supported_exts)
        if root_imgs:
            grouped["_root"] = []
            for p in root_imgs:
                key = f"_root/{p.name}"
                dec = decisions.get(key, {})
                grouped["_root"].append(
                    {
                        "car_id": "_root",
                        "filename": p.name,
                        "reason": _lookup_logged_reason("_root", p.name, state_file, car_state_dir)
                        if is_review
                        else "ok",
                        "status": dec.get("status", "pending") if is_review else "ready",
                        "updated_at": dec.get("updated_at", ""),
                    }
                )

        subfolders = sorted(
            [d for d in base_folder.iterdir() if d.is_dir() and not d.name.startswith("_")],
            key=lambda d: d.name.lower(),
        )
        for car_folder in subfolders:
            cid = car_folder.name
            imgs = list_supported_images(car_folder, supported_exts)
            if not imgs:
                continue
            grouped[cid] = []
            for p in imgs:
                key = f"{cid}/{p.name}"
                dec = decisions.get(key, {})
                grouped[cid].append(
                    {
                        "car_id": cid,
                        "filename": p.name,
                        "reason": _lookup_logged_reason(cid, p.name, state_file, car_state_dir)
                        if is_review
                        else "ok",
                        "status": dec.get("status", "pending") if is_review else "ready",
                        "updated_at": dec.get("updated_at", ""),
                    }
                )
        return grouped

    def _find_plate_covered_base(car_id: str, stem: str) -> np.ndarray | None:
        """Find or generate the plate-covered BGR car image (before template framing) so any ratio can be rendered cleanly."""
        cache_file = output_dir / "_covered_cache" / car_id / f"{stem}.jpg"
        if cache_file.exists():
            return load_image_bgr(cache_file)

        # Otherwise check if raw photo exists in inbox_dir/<car_id> or data/test_photos
        search_dirs = [
            inbox_dir / car_id,
            Path(paths_cfg.get("input_dir", "data/test_photos")),
        ]
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for ext in supported_exts:
                cand = sdir / f"{stem}{ext}"
                if cand.exists():
                    bgr = load_image_bgr(cand)
                    dets = _get_detector().detect_array(bgr, min_conf=low_conf_floor)
                    if dets:
                        ov = apply_plate_overlays(bgr, dets, settings, overlay_bgra)
                        cache_file.parent.mkdir(parents=True, exist_ok=True)
                        cv2.imwrite(str(cache_file), ov.image_bgr)
                        return ov.image_bgr
                    return bgr
        return None

    @app.get("/", response_class=HTMLResponse)
    def index(_user: str = Depends(verify_auth)) -> HTMLResponse:
        """Render the Stitch-aligned Forest Wheel Plate Removal System UI."""
        # Ensure we include review car IDs or filenames in initial HTML for compatibility
        rev_cars = _discover_folder_tree(review_dir, is_review=True)
        extra_meta = json.dumps(rev_cars)
        page = STITCH_UI_HTML.replace(
            "</body>",
            f'<script id="initial-review-preload" type="application/json">{extra_meta}</script></body>',
        )
        return HTMLResponse(content=page)

    @app.get("/api/items")
    def api_list_items(_user: str = Depends(verify_auth)) -> JSONResponse:
        """Return JSON list of cars and images currently in review/."""
        return JSONResponse(content={"cars": _discover_folder_tree(review_dir, is_review=True)})

    @app.get("/api/state")
    def api_state(_user: str = Depends(verify_auth)) -> JSONResponse:
        """Return complete state of both output/ and review/ car galleries."""
        return JSONResponse(
            content={
                "cars_output": _discover_folder_tree(output_dir, is_review=False),
                "cars_review": _discover_folder_tree(review_dir, is_review=True),
            }
        )

    @app.post("/api/upload")
    async def api_upload(
        car_id: str = Form("FW-BATCH"),
        ratio: str = Form("16:9"),
        files: list[UploadFile] = File(...),
        _user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Accept multiple uploaded vehicle photos, cover plates, and compose into selected ratio."""
        clean_cid = _sanitize_car_id(car_id)
        profile_name = resolve_ratio_profile(ratio, default_profile="ratio_16_9")

        car_inbox = inbox_dir / clean_cid
        car_out = output_dir / clean_cid
        car_rev = review_dir / clean_cid
        car_inbox.mkdir(parents=True, exist_ok=True)

        saved_files: list[Path] = []
        ext_set = {e.lower() for e in supported_exts}
        for up in files:
            raw_name = Path(up.filename or "photo.jpg").name
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name)
            suffix = Path(safe_name).suffix.lower()
            if suffix not in ext_set:
                continue
            dest = car_inbox / safe_name
            content = await up.read()
            dest.write_bytes(content)
            saved_files.append(dest)

        if not saved_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No supported image files uploaded. Supported: {supported_exts}",
            )

        car_state_json = state_file.parent / f"images_{clean_cid}.json"
        records = run_pipeline(
            input_dir=car_inbox,
            output_dir=car_out,
            review_dir=car_rev,
            config_path=config_path,
            state_file=car_state_json,
            profile=profile_name,
            force=True,
            detector=_get_detector(),
        )

        # Also cache the plate-covered base image (before template border) so user can switch
        # between 1:1, 16:9, and 9:16 dynamically in Vehicle Galleries without re-cropping a border.
        cache_dir = output_dir / "_covered_cache" / clean_cid
        cache_dir.mkdir(parents=True, exist_ok=True)
        for rec in records:
            if rec.destination == "output":
                src_p = car_inbox / rec.filename
                if src_p.exists():
                    bgr = load_image_bgr(src_p)
                    dets = _get_detector().detect_array(bgr)
                    ov = apply_plate_overlays(bgr, dets, settings, overlay_bgra)
                    cv2.imwrite(str(cache_dir / f"{src_p.stem}.jpg"), ov.image_bgr)

        out_count = sum(1 for r in records if r.destination == "output")
        rev_count = sum(1 for r in records if r.destination == "review")

        return JSONResponse(
            content={
                "ok": True,
                "car_id": clean_cid,
                "ratio": ratio,
                "profile": profile_name,
                "processed_count": len(records),
                "output_count": out_count,
                "review_count": rev_count,
                "records": [
                    {
                        "filename": r.filename,
                        "plates_found": r.plates_found,
                        "confidence": r.max_confidence,
                        "overlay_mode": r.overlay_mode,
                        "destination": r.destination,
                        "reason": r.reason,
                    }
                    for r in records
                ],
            }
        )

    @app.post("/api/demo-batch")
    def api_demo_batch(
        car_id: str = Query("FW-2026-911GT3"),
        ratio: str = Query("16:9"),
        _user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Copy sample photos from data/test_photos into a car batch and run the pipeline."""
        clean_cid = _sanitize_car_id(car_id)
        profile_name = resolve_ratio_profile(ratio, default_profile="ratio_16_9")
        sample_src = Path(paths_cfg.get("input_dir", "data/test_photos"))
        if not sample_src.exists():
            raise HTTPException(status_code=404, detail="Sample test_photos directory not found.")

        car_inbox = inbox_dir / clean_cid
        car_inbox.mkdir(parents=True, exist_ok=True)
        for p in list_supported_images(sample_src, supported_exts):
            shutil.copy2(p, car_inbox / p.name)

        car_state_json = state_file.parent / f"images_{clean_cid}.json"
        records = run_pipeline(
            input_dir=car_inbox,
            output_dir=output_dir / clean_cid,
            review_dir=review_dir / clean_cid,
            config_path=config_path,
            state_file=car_state_json,
            profile=profile_name,
            force=True,
            detector=_get_detector(),
        )
        return JSONResponse(
            content={
                "ok": True,
                "car_id": clean_cid,
                "processed_count": len(records),
            }
        )

    @app.get("/media/before/{car_id}/{filename}")
    def media_before(
        car_id: str, filename: str, _user: str = Depends(verify_auth)
    ) -> Response:
        """Serve authenticated 'Before' thumbnail of a review image."""
        img_path = _resolve_child_file(review_dir, car_id, filename)
        bgr = load_image_bgr(img_path)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        jpeg_bytes = _pil_to_jpeg_bytes(Image.fromarray(rgb), max_width=thumb_width)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.get("/media/after/{car_id}/{filename}")
    def media_after(
        car_id: str,
        filename: str,
        ratio: str = Query("16:9"),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Serve authenticated 'After' template preview thumbnail of a review image in 1:1, 16:9, or 9:16."""
        img_path = _resolve_child_file(review_dir, car_id, filename)
        profile_name = resolve_ratio_profile(ratio, default_profile="website")
        composed_pil = _render_composed_image(
            img_path=img_path,
            settings=settings,
            template_cfg=template_cfg,
            detector=_get_detector(),
            overlay_bgra=overlay_bgra,
            profile_name=profile_name,
            low_conf_floor=low_conf_floor,
        )
        jpeg_bytes = _pil_to_jpeg_bytes(composed_pil, max_width=thumb_width)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.get("/media/output/{car_id}/{filename}")
    def media_output(
        car_id: str,
        filename: str,
        ratio: str = Query("16:9"),
        download: int = Query(0),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Serve or download a processed output image dynamically rendered in 1:1, 16:9, or 9:16."""
        out_path = _resolve_child_file(output_dir, car_id, filename)
        profile_name = resolve_ratio_profile(ratio, default_profile="ratio_16_9")

        covered_bgr = _find_plate_covered_base(car_id, out_path.stem)
        if covered_bgr is not None:
            pil_img = compose_template(covered_bgr, template_cfg, profile_name=profile_name)
        else:
            bgr = load_image_bgr(out_path)
            pil_img = compose_template(bgr, template_cfg, profile_name=profile_name)

        max_w = 0 if download else thumb_width
        jpeg_bytes = _pil_to_jpeg_bytes(pil_img, max_width=max_w, quality=jpeg_quality)
        headers = {"Cache-Control": "private, no-store"}
        if download:
            dl_name = f"{car_id}_{ratio.replace(':', 'x')}_{filename}"
            headers["Content-Disposition"] = f'attachment; filename="{dl_name}"'
        return Response(content=jpeg_bytes, media_type="image/jpeg", headers=headers)

    @app.get("/api/export/{car_id}")
    def api_export_zip(
        car_id: str,
        ratio: str = Query("16:9"),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Export all processed photos for a Car ID as a ZIP archive in the selected ratio (1:1, 16:9, 9:16)."""
        safe_car = _validate_path_segment(car_id)
        target_dir = output_dir if safe_car == "_root" else (output_dir / safe_car)
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail="Car output folder not found.")

        imgs = list_supported_images(target_dir, supported_exts)
        if not imgs:
            raise HTTPException(status_code=404, detail="No processed images found for car.")

        profile_name = resolve_ratio_profile(ratio, default_profile="ratio_16_9")
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in imgs:
                covered_bgr = _find_plate_covered_base(safe_car, p.stem)
                if covered_bgr is not None:
                    pil_img = compose_template(covered_bgr, template_cfg, profile_name=profile_name)
                else:
                    pil_img = compose_template(load_image_bgr(p), template_cfg, profile_name=profile_name)
                img_bytes = _pil_to_jpeg_bytes(pil_img, max_width=0, quality=jpeg_quality)
                zf.writestr(f"{p.stem}_{ratio.replace(':', 'x')}.jpg", img_bytes)

        zip_filename = f"{safe_car}_{ratio.replace(':', 'x')}_export.zip"
        return Response(
            content=zip_buf.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
        )

    @app.get("/api/studio-preview")
    def api_studio_preview(
        ratio: str = Query("16:9"),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Render a live sample vehicle preview in the Template Studio for 1:1, 16:9, or 9:16."""
        profile_name = resolve_ratio_profile(ratio, default_profile="ratio_16_9")
        sample_candidates = list_supported_images(
            Path(paths_cfg.get("input_dir", "data/test_photos")), supported_exts
        )
        if sample_candidates:
            sample_bgr = load_image_bgr(sample_candidates[0])
            dets = _get_detector().detect_array(sample_bgr, min_conf=low_conf_floor)
            if dets:
                sample_bgr = apply_plate_overlays(sample_bgr, dets, settings, overlay_bgra).image_bgr
        else:
            sample_bgr = np.full((720, 1280, 3), (35, 65, 50), dtype=np.uint8)

        composed = compose_template(sample_bgr, template_cfg, profile_name=profile_name)
        jpeg_bytes = _pil_to_jpeg_bytes(composed, max_width=900, quality=90)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.post("/api/approve/{car_id}/{filename}")
    def api_approve(
        car_id: str,
        filename: str,
        ratio: str = Query("website"),
        payload: dict[str, Any] | None = Body(default=None),
        user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Approve a review image: compose template, write to output/, remove from review/."""
        img_path = _resolve_child_file(review_dir, car_id, filename)
        profile_name = resolve_ratio_profile(ratio, default_profile="website")
        quad_pct = payload.get("quad_pct") if isinstance(payload, dict) else None

        composed_pil = _render_composed_image(
            img_path=img_path,
            settings=settings,
            template_cfg=template_cfg,
            detector=_get_detector(),
            overlay_bgra=overlay_bgra,
            profile_name=profile_name,
            low_conf_floor=low_conf_floor,
            custom_quad_pct=quad_pct,
        )

        target_dir = output_dir if car_id == "_root" else (output_dir / car_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{img_path.stem}.jpg"
        composed_pil.save(out_path, format="JPEG", quality=jpeg_quality)

        img_path.unlink()

        decisions = _load_json_dict(decisions_file)
        key = f"{car_id}/{filename}"
        decisions[key] = {
            "status": "approved",
            "approved_by": user,
            "ratio": ratio,
            "output_path": str(out_path),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_json_dict(decisions_file, decisions)
        logger.info("Approved review item %s -> %s (by %s)", key, out_path, user)

        return JSONResponse(
            content={
                "ok": True,
                "car_id": car_id,
                "filename": filename,
                "status": "approved",
                "output_path": str(out_path),
            }
        )

    @app.post("/api/reject/{car_id}/{filename}")
    def api_reject(
        car_id: str, filename: str, user: str = Depends(verify_auth)
    ) -> JSONResponse:
        """Reject a review image: leave in review/ and mark status as 'rejected'."""
        _resolve_child_file(review_dir, car_id, filename)
        decisions = _load_json_dict(decisions_file)
        key = f"{car_id}/{filename}"
        decisions[key] = {
            "status": "rejected",
            "rejected_by": user,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_json_dict(decisions_file, decisions)
        logger.info("Rejected review item %s (by %s)", key, user)

        return JSONResponse(
            content={
                "ok": True,
                "car_id": car_id,
                "filename": filename,
                "status": "rejected",
            }
        )

    return app
