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

from fwphotos.compose import (
    compose_template,
    load_template_config,
    render_apple_frame_studio,
)
from fwphotos.detect import (
    PlateDetector,
    list_supported_images,
    load_image_bgr,
    load_settings,
)
from fwphotos.overlay import (
    apply_plate_overlays,
    estimate_plate_corners,
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
    cars_meta_file = state_file.parent / "cars_metadata.json"
    frame_config_file = state_file.parent / "frame_config.json"
    custom_overlay_file = state_file.parent / "custom_plate_overlay.png"
    car_state_file_cfg = sync_cfg.get("car_state_file")
    car_state_dir = Path(car_state_file_cfg).parent if car_state_file_cfg else state_file.parent

    template_path = Path(paths_cfg.get("template_config", "config/template.yaml"))
    template_cfg = load_template_config(template_path)

    overlay_path = Path(
        paths_cfg.get("plate_overlay_asset", "assets/plate_overlay.png")
    )
    overlay_bgra = (
        load_overlay_rgba(custom_overlay_file)
        if custom_overlay_file.exists()
        else (load_overlay_rgba(overlay_path) if overlay_path.exists() else None)
    )

    def _get_frame_config() -> dict[str, Any]:
        """Return the active pre-selected Frame configuration (defaults to Clean White, Fit to frame, 1:1)."""
        cfg = _load_json_dict(frame_config_file)
        return {
            "ratio": str(cfg.get("ratio", "1:1")),
            "fit_mode": str(cfg.get("fit_mode", "fit")),
            "template_style": str(cfg.get("template_style", "clean_white")),
            "offset_x": float(cfg.get("offset_x", 0.5)),
            "offset_y": float(cfg.get("offset_y", 0.5)),
            "caption_enabled": bool(cfg.get("caption_enabled", True)),
            "car_model": str(cfg.get("car_model", "Forest Wheel Showroom")),
            "car_price": str(cfg.get("car_price", "")),
            "car_specs": str(cfg.get("car_specs", "Verified Quality Pre-Owned • Singapore")),
            "has_custom_overlay": custom_overlay_file.exists(),
        }

    def _render_with_active_frame_config(
        covered_bgr: np.ndarray,
        car_id: str | None = None,
        ratio_override: str | None = None,
        fit_mode_override: str | None = None,
        template_style_override: str | None = None,
    ) -> Image.Image:
        """Render a plate-covered BGR photo using the pre-selected Frame configuration across any ratio."""
        fcfg = _get_frame_config()
        all_meta = _load_json_dict(cars_meta_file)
        car_meta = all_meta.get(car_id or "", {}) if car_id else {}

        target_ratio = ratio_override or fcfg["ratio"]
        target_fit_mode = fit_mode_override or fcfg["fit_mode"]
        target_template_style = template_style_override or fcfg["template_style"]
        model_str = car_meta.get("car_model") if "car_model" in car_meta else fcfg["car_model"]
        # If the car was uploaded with an empty price, keep it empty so no price is rendered in the frame
        price_str = car_meta.get("car_price", "") if car_meta else fcfg["car_price"]
        specs_str = car_meta.get("car_specs", "") if "car_specs" in car_meta else fcfg["car_specs"]

        return render_apple_frame_studio(
            image_bgr=covered_bgr,
            ratio=target_ratio,
            fit_mode=target_fit_mode,
            template_style=target_template_style,
            offset_x=fcfg["offset_x"],
            offset_y=fcfg["offset_y"],
            caption_enabled=fcfg["caption_enabled"],
            car_model=str(model_str or ""),
            car_price=str(price_str or ""),
            car_specs=str(specs_str or ""),
        )

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
        """Return complete state of both output/ and review/ car galleries, metadata, and Frame configuration."""
        return JSONResponse(
            content={
                "cars_output": _discover_folder_tree(output_dir, is_review=False),
                "cars_review": _discover_folder_tree(review_dir, is_review=True),
                "cars_meta": _load_json_dict(cars_meta_file),
                "frame_config": _get_frame_config(),
            }
        )

    @app.get("/api/frame-config")
    def api_get_frame_config(_user: str = Depends(verify_auth)) -> JSONResponse:
        """Return the pre-selected Frame configuration."""
        return JSONResponse(content={"ok": True, "frame_config": _get_frame_config()})

    @app.post("/api/frame-config")
    def api_save_frame_config(
        payload: dict[str, Any] = Body(...),
        _user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Save the global Frame configuration and re-apply it to existing output photos."""
        cur = _get_frame_config()
        new_cfg = {
            "ratio": str(payload.get("ratio", cur["ratio"])),
            "fit_mode": str(payload.get("fit_mode", cur["fit_mode"])),
            "template_style": str(payload.get("template_style", cur["template_style"])),
            "offset_x": float(payload.get("offset_x", cur["offset_x"])),
            "offset_y": float(payload.get("offset_y", cur["offset_y"])),
            "caption_enabled": bool(payload.get("caption_enabled", cur["caption_enabled"])),
            "car_model": str(payload.get("car_model", cur["car_model"])),
            "car_price": str(payload.get("car_price", cur["car_price"])),
            "car_specs": str(payload.get("car_specs", cur["car_specs"])),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_json_dict(frame_config_file, new_cfg)

        # Re-render all existing output photos with the newly saved Frame configuration
        out_tree = _discover_folder_tree(output_dir, is_review=False)
        updated_files = 0
        for cid, items in out_tree.items():
            target_d = output_dir if cid == "_root" else (output_dir / cid)
            for item in items:
                fname = item["filename"]
                stem = Path(fname).stem
                covered_bgr = _find_plate_covered_base(cid, stem)
                if covered_bgr is not None:
                    framed_pil = _render_with_active_frame_config(
                        covered_bgr, car_id=cid, ratio_override=new_cfg["ratio"]
                    )
                    out_p = target_d / fname
                    framed_pil.convert("RGB").save(out_p, format="JPEG", quality=jpeg_quality)
                    updated_files += 1

        return JSONResponse(
            content={
                "ok": True,
                "frame_config": _get_frame_config(),
                "updated_files": updated_files,
            }
        )

    @app.post("/api/plate-overlay")
    async def api_upload_plate_overlay(
        file: UploadFile = File(...),
        _user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Upload a custom image to cover the license plate across all photos."""
        nonlocal overlay_bgra
        raw_bytes = await file.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Empty overlay file.")

        try:
            with Image.open(io.BytesIO(raw_bytes)) as pil_ov:
                rgba = pil_ov.convert("RGBA")
                custom_overlay_file.parent.mkdir(parents=True, exist_ok=True)
                rgba.save(custom_overlay_file, format="PNG")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400, detail=f"Invalid image file for plate overlay: {exc}"
            ) from exc

        overlay_bgra = load_overlay_rgba(custom_overlay_file)

        # Clear cached plate-covered base images so existing cars re-render with the new plate cover
        cache_root = output_dir / "_covered_cache"
        if cache_root.exists():
            shutil.rmtree(cache_root, ignore_errors=True)

        # Re-render existing output photos with the new plate cover and active frame config
        out_tree = _discover_folder_tree(output_dir, is_review=False)
        for cid, items in out_tree.items():
            target_d = output_dir if cid == "_root" else (output_dir / cid)
            for item in items:
                fname = item["filename"]
                stem = Path(fname).stem
                covered_bgr = _find_plate_covered_base(cid, stem)
                if covered_bgr is not None:
                    framed_pil = _render_with_active_frame_config(covered_bgr, car_id=cid)
                    framed_pil.convert("RGB").save(target_d / fname, format="JPEG", quality=jpeg_quality)

        return JSONResponse(
            content={
                "ok": True,
                "has_custom_overlay": True,
                "filename": file.filename or "custom_plate_overlay.png",
            }
        )

    @app.delete("/api/plate-overlay")
    def api_reset_plate_overlay(_user: str = Depends(verify_auth)) -> JSONResponse:
        """Reset the plate cover overlay back to the default Forest Wheel plate_overlay.png."""
        nonlocal overlay_bgra
        if custom_overlay_file.exists():
            custom_overlay_file.unlink(missing_ok=True)
        overlay_bgra = load_overlay_rgba(overlay_path) if overlay_path.exists() else None

        cache_root = output_dir / "_covered_cache"
        if cache_root.exists():
            shutil.rmtree(cache_root, ignore_errors=True)

        return JSONResponse(content={"ok": True, "has_custom_overlay": False})

    @app.get("/media/plate-overlay")
    def media_plate_overlay(_user: str = Depends(verify_auth)) -> Response:
        """Serve the currently active license plate cover image (custom or default)."""
        active_p = custom_overlay_file if custom_overlay_file.exists() else overlay_path
        if active_p.exists():
            return Response(
                content=active_p.read_bytes(),
                media_type="image/png",
                headers={"Cache-Control": "private, no-store"},
            )
        # Fallback synthetic preview
        blank = Image.new("RGB", (400, 110), (20, 45, 35))
        return Response(
            content=_pil_to_jpeg_bytes(blank),
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.post("/api/upload")
    async def api_upload(
        car_id: str = Form("FW-BATCH"),
        ratio: str = Form("16:9"),
        car_model: str = Form(""),
        car_price: str = Form(""),
        car_specs: str = Form(""),
        masking_style: str = Form("clean_blank"),
        files: list[UploadFile] = File(...),
        _user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Accept multiple uploaded vehicle photos, cover plates, and compose into selected ratio."""
        clean_cid = _sanitize_car_id(car_id)
        profile_name = resolve_ratio_profile(ratio, default_profile="ratio_16_9")

        # Save car metadata (plate display string, model, price, specs, masking style)
        # Note: if car_price is empty, store "" so no price is displayed on the frame.
        all_meta = _load_json_dict(cars_meta_file)
        cur_meta = all_meta.get(clean_cid, {})
        all_meta[clean_cid] = {
            "plate_display": car_id.strip() or clean_cid,
            "car_model": car_model.strip() or cur_meta.get("car_model", f"Vehicle {clean_cid}"),
            "car_price": car_price.strip(),
            "car_specs": car_specs.strip(),
            "masking_style": masking_style.strip() or cur_meta.get("masking_style", "clean_blank"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_json_dict(cars_meta_file, all_meta)

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

        # Also cache the plate-covered base image (using active custom or default plate cover)
        # and compose the output photo using the pre-selected Frame configuration from the Frame page.
        active_fcfg = _get_frame_config()
        effective_ratio = ratio if ratio else active_fcfg["ratio"]
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
                    framed_pil = _render_with_active_frame_config(
                        ov.image_bgr, car_id=clean_cid, ratio_override=effective_ratio
                    )
                    out_file = car_out / f"{src_p.stem}.jpg"
                    framed_pil.convert("RGB").save(out_file, format="JPEG", quality=jpeg_quality)

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
        active_fcfg = _get_frame_config()
        effective_ratio = ratio if ratio else active_fcfg["ratio"]
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
                    framed_pil = _render_with_active_frame_config(
                        ov.image_bgr, car_id=clean_cid, ratio_override=effective_ratio
                    )
                    out_file = (output_dir / clean_cid) / f"{src_p.stem}.jpg"
                    framed_pil.convert("RGB").save(out_file, format="JPEG", quality=jpeg_quality)
        return JSONResponse(
            content={
                "ok": True,
                "car_id": clean_cid,
                "processed_count": len(records),
            }
        )

    @app.get("/media/before/{car_id}/{filename}")
    def media_before(
        car_id: str,
        filename: str,
        full: int = Query(0),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Serve authenticated 'Before' thumbnail (or full resolution) of a review image."""
        img_path = _resolve_child_file(review_dir, car_id, filename)
        bgr = load_image_bgr(img_path)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        max_w = 0 if full else thumb_width
        jpeg_bytes = _pil_to_jpeg_bytes(Image.fromarray(rgb), max_width=max_w, quality=jpeg_quality)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.get("/media/after/{car_id}/{filename}")
    def media_after(
        car_id: str,
        filename: str,
        ratio: str | None = Query(default=None),
        full: int = Query(0),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Serve authenticated 'After' framed preview of a review image using the pre-selected Frame config."""
        img_path = _resolve_child_file(review_dir, car_id, filename)
        image_bgr = load_image_bgr(img_path)
        dets = _get_detector().detect_array(image_bgr, min_conf=low_conf_floor)
        if dets:
            processed_bgr = apply_plate_overlays(image_bgr, dets, settings, overlay_bgra).image_bgr
        else:
            processed_bgr = image_bgr
        composed_pil = _render_with_active_frame_config(
            processed_bgr, car_id=car_id, ratio_override=ratio
        )
        max_w = 0 if full else thumb_width
        jpeg_bytes = _pil_to_jpeg_bytes(composed_pil, max_width=max_w, quality=jpeg_quality)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.get("/media/output/{car_id}/{filename}")
    def media_output(
        car_id: str,
        filename: str,
        ratio: str | None = Query(default=None),
        download: int = Query(0),
        full: int = Query(0),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Serve or download a processed output image rendered with the pre-selected Frame config across any ratio."""
        out_path = _resolve_child_file(output_dir, car_id, filename)
        active_fcfg = _get_frame_config()
        effective_ratio = ratio or active_fcfg["ratio"]

        covered_bgr = _find_plate_covered_base(car_id, out_path.stem)
        if covered_bgr is not None:
            pil_img = _render_with_active_frame_config(
                covered_bgr, car_id=car_id, ratio_override=effective_ratio
            )
        else:
            bgr = load_image_bgr(out_path)
            pil_img = _render_with_active_frame_config(
                bgr, car_id=car_id, ratio_override=effective_ratio
            )

        max_w = 0 if (download or full) else thumb_width
        jpeg_bytes = _pil_to_jpeg_bytes(pil_img, max_width=max_w, quality=jpeg_quality)
        headers = {"Cache-Control": "private, no-store"}
        if download:
            dl_name = f"{car_id}_{effective_ratio.replace(':', 'x')}_{filename}"
            headers["Content-Disposition"] = f'attachment; filename="{dl_name}"'
        return Response(content=jpeg_bytes, media_type="image/jpeg", headers=headers)

    @app.get("/api/export/{car_id}")
    def api_export_zip(
        car_id: str,
        ratio: str | None = Query(default=None),
        fit_mode: str | None = Query(default=None),
        template_style: str | None = Query(default=None),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Export all processed photos for a Car ID as a ZIP archive using the pre-selected Frame config."""
        safe_car = _validate_path_segment(car_id)
        target_dir = output_dir if safe_car == "_root" else (output_dir / safe_car)
        if not target_dir.exists():
            raise HTTPException(status_code=404, detail="Car output folder not found.")

        imgs = list_supported_images(target_dir, supported_exts)
        if not imgs:
            raise HTTPException(status_code=404, detail="No processed images found for car.")

        active_fcfg = _get_frame_config()
        effective_ratio = ratio or active_fcfg["ratio"]
        effective_fit_mode = fit_mode or active_fcfg["fit_mode"]
        effective_template_style = template_style or active_fcfg["template_style"]
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in imgs:
                covered_bgr = _find_plate_covered_base(safe_car, p.stem)
                if covered_bgr is not None:
                    pil_img = _render_with_active_frame_config(
                        covered_bgr,
                        car_id=safe_car,
                        ratio_override=effective_ratio,
                        fit_mode_override=effective_fit_mode,
                        template_style_override=effective_template_style,
                    )
                else:
                    pil_img = _render_with_active_frame_config(
                        load_image_bgr(p),
                        car_id=safe_car,
                        ratio_override=effective_ratio,
                        fit_mode_override=effective_fit_mode,
                        template_style_override=effective_template_style,
                    )
                img_bytes = _pil_to_jpeg_bytes(pil_img, max_width=0, quality=jpeg_quality)
                zf.writestr(f"{p.stem}_{effective_ratio.replace(':', 'x')}.jpg", img_bytes)

        zip_filename = f"{safe_car}_{effective_ratio.replace(':', 'x')}_export.zip"
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
        ratio: str | None = Query(default=None),
        payload: dict[str, Any] | None = Body(default=None),
        user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Approve a review image: compose with pre-selected Frame config, write to output/, remove from review/."""
        img_path = _resolve_child_file(review_dir, car_id, filename)
        quad_pct = payload.get("quad_pct") if isinstance(payload, dict) else None

        image_bgr = load_image_bgr(img_path)
        img_h, img_w = image_bgr.shape[:2]
        if quad_pct and len(quad_pct) == 4 and overlay_bgra is not None:
            pts = np.array(
                [[p[0] * img_w / 100.0, p[1] * img_h / 100.0] for p in quad_pct],
                dtype=np.float32,
            )
            feather_px = int(settings.get("overlay", {}).get("feather_px", 5))
            processed_bgr = warp_and_composite_single(
                image_bgr, overlay_bgra, pts, feather_px=feather_px
            )
        else:
            dets = _get_detector().detect_array(image_bgr, min_conf=low_conf_floor)
            if dets:
                processed_bgr = apply_plate_overlays(image_bgr, dets, settings, overlay_bgra).image_bgr
            else:
                processed_bgr = image_bgr

        cache_f = output_dir / "_covered_cache" / car_id / f"{img_path.stem}.jpg"
        cache_f.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(cache_f), processed_bgr)

        active_fcfg = _get_frame_config()
        effective_ratio = ratio if (ratio and ratio != "website") else active_fcfg["ratio"]
        composed_pil = _render_with_active_frame_config(
            processed_bgr, car_id=car_id, ratio_override=effective_ratio
        )

        target_dir = output_dir if car_id == "_root" else (output_dir / car_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{img_path.stem}.jpg"
        composed_pil.convert("RGB").save(out_path, format="JPEG", quality=jpeg_quality)

        img_path.unlink()

        decisions = _load_json_dict(decisions_file)
        key = f"{car_id}/{filename}"
        decisions[key] = {
            "status": "approved",
            "approved_by": user,
            "ratio": effective_ratio,
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

    @app.get("/media/original/{car_id}/{filename}")
    def media_original(
        car_id: str,
        filename: str,
        full: int = Query(0),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Serve authenticated original ('Before' plate removal) photo for any car in Gallery."""
        safe_car = _validate_path_segment(car_id)
        safe_name = _validate_path_segment(filename)
        stem = Path(safe_name).stem

        # Search inbox/<car_id>, review/<car_id>, data/test_photos, and output/<car_id>
        search_dirs = [
            inbox_dir if safe_car == "_root" else (inbox_dir / safe_car),
            review_dir if safe_car == "_root" else (review_dir / safe_car),
            Path(paths_cfg.get("input_dir", "data/test_photos")),
            output_dir if safe_car == "_root" else (output_dir / safe_car),
        ]
        found_path: Path | None = None
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            exact = sdir / safe_name
            if exact.is_file():
                found_path = exact
                break
            for ext in supported_exts:
                cand = sdir / f"{stem}{ext}"
                if cand.is_file():
                    found_path = cand
                    break
            if found_path:
                break

        if found_path is None:
            raise HTTPException(status_code=404, detail="Original image not found.")

        bgr = load_image_bgr(found_path)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        max_w = 0 if full else thumb_width
        jpeg_bytes = _pil_to_jpeg_bytes(Image.fromarray(rgb), max_width=max_w, quality=jpeg_quality)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.get("/media/clean/{car_id}/{filename}")
    def media_clean(
        car_id: str,
        filename: str,
        full: int = Query(0),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Serve authenticated plate-removed ('After' plate removal, frameless) image for Gallery & Frame Studio."""
        safe_car = _validate_path_segment(car_id)
        safe_name = _validate_path_segment(filename)
        stem = Path(safe_name).stem

        covered_bgr = _find_plate_covered_base(safe_car, stem)
        if covered_bgr is None:
            # Check review_dir or output_dir
            for base_d in (review_dir, output_dir):
                target_d = base_d if safe_car == "_root" else (base_d / safe_car)
                cand = target_d / safe_name
                if cand.is_file():
                    bgr = load_image_bgr(cand)
                    dets = _get_detector().detect_array(bgr, min_conf=low_conf_floor)
                    if dets:
                        covered_bgr = apply_plate_overlays(bgr, dets, settings, overlay_bgra).image_bgr
                    else:
                        covered_bgr = bgr
                    break

        if covered_bgr is None:
            raise HTTPException(status_code=404, detail="Plate-removed image not found.")

        rgb = cv2.cvtColor(covered_bgr, cv2.COLOR_BGR2RGB)
        max_w = 0 if full else thumb_width
        jpeg_bytes = _pil_to_jpeg_bytes(Image.fromarray(rgb), max_width=max_w, quality=jpeg_quality)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.put("/api/cars/{car_id}")
    def api_update_car(
        car_id: str,
        payload: dict[str, Any] = Body(...),
        user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Edit or rename a car group (plate number tag, car model, price, specs)."""
        safe_car = _validate_path_segment(car_id)
        new_raw_id = str(payload.get("new_car_id", safe_car)).strip()
        new_cid = _sanitize_car_id(new_raw_id) if new_raw_id != "_root" else "_root"

        all_meta = _load_json_dict(cars_meta_file)
        existing_meta = all_meta.pop(safe_car, {})

        # If folder slug changed, rename folders across output_dir, review_dir, inbox_dir, and _covered_cache
        if new_cid != safe_car and safe_car != "_root" and new_cid != "_root":
            for folder_root in (
                output_dir,
                review_dir,
                inbox_dir,
                output_dir / "_covered_cache",
            ):
                src_f = folder_root / safe_car
                dst_f = folder_root / new_cid
                if src_f.exists():
                    dst_f.parent.mkdir(parents=True, exist_ok=True)
                    if dst_f.exists():
                        for item in src_f.iterdir():
                            shutil.move(str(item), str(dst_f / item.name))
                        shutil.rmtree(src_f, ignore_errors=True)
                    else:
                        src_f.rename(dst_f)

            # Rename per-car state file if present
            old_state = state_file.parent / f"images_{safe_car}.json"
            new_state = state_file.parent / f"images_{new_cid}.json"
            if old_state.exists():
                old_state.rename(new_state)

        all_meta[new_cid] = {
            "plate_display": str(payload.get("plate_display", new_raw_id or new_cid)).strip(),
            "car_model": str(payload.get("car_model", existing_meta.get("car_model", ""))).strip(),
            "car_price": str(payload.get("car_price", existing_meta.get("car_price", ""))).strip(),
            "car_specs": str(payload.get("car_specs", existing_meta.get("car_specs", ""))).strip(),
            "masking_style": str(payload.get("masking_style", existing_meta.get("masking_style", "clean_blank"))).strip(),
            "updated_by": user,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_json_dict(cars_meta_file, all_meta)

        return JSONResponse(
            content={
                "ok": True,
                "old_car_id": safe_car,
                "car_id": new_cid,
                "meta": all_meta[new_cid],
            }
        )

    def _delete_single_photo_files(cid: str, fname: str) -> int:
        """Delete a single photo from output/, review/, inbox/, and _covered_cache/ (never touching data/test_photos)."""
        safe_c = _validate_path_segment(cid)
        safe_f = _validate_path_segment(fname)
        stem = Path(safe_f).stem
        removed = 0

        for base_d in (output_dir, review_dir, inbox_dir):
            target_d = base_d if safe_c == "_root" else (base_d / safe_c)
            if not target_d.exists():
                continue
            exact = target_d / safe_f
            if exact.is_file():
                exact.unlink()
                removed += 1
            for ext in supported_exts:
                cand = target_d / f"{stem}{ext}"
                if cand.is_file():
                    cand.unlink()
                    removed += 1
            # Clean up empty car folder
            if safe_c != "_root" and target_d.exists() and not any(target_d.iterdir()):
                shutil.rmtree(target_d, ignore_errors=True)

        cache_f = output_dir / "_covered_cache" / safe_c / f"{stem}.jpg"
        if cache_f.is_file():
            cache_f.unlink()

        return 1 if removed > 0 else 0

    def _delete_entire_car_group(cid: str) -> int:
        """Delete an entire car group across output/, review/, inbox/, and metadata."""
        safe_c = _validate_path_segment(cid)
        count = 0
        for base_d in (output_dir, review_dir):
            target_d = base_d if safe_c == "_root" else (base_d / safe_c)
            if target_d.exists():
                imgs = list_supported_images(target_d, supported_exts)
                count += len(imgs)
                if safe_c == "_root":
                    for p in imgs:
                        p.unlink(missing_ok=True)
                else:
                    shutil.rmtree(target_d, ignore_errors=True)

        if safe_c != "_root":
            for extra_d in (inbox_dir / safe_c, output_dir / "_covered_cache" / safe_c):
                if extra_d.exists():
                    shutil.rmtree(extra_d, ignore_errors=True)
            car_st = state_file.parent / f"images_{safe_c}.json"
            if car_st.exists():
                car_st.unlink(missing_ok=True)

        all_meta = _load_json_dict(cars_meta_file)
        if safe_c in all_meta:
            all_meta.pop(safe_c, None)
            _save_json_dict(cars_meta_file, all_meta)

        return count

    @app.post("/api/delete")
    def api_delete(
        payload: dict[str, Any] = Body(...),
        user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Delete single photo, multi-selected photos, an entire car group, or all photos in inventory.

        Supported payload formats:
        - {"scope": "selected", "items": [{"car_id": "SXX1234A", "filename": "01.jpg"}, ...]}
        - {"scope": "car", "car_id": "SXX1234A"} or {"scope": "car", "car_ids": ["SXX1234A", ...]}
        - {"scope": "all"}
        """
        scope = str(payload.get("scope", "selected")).strip().lower()
        deleted_photos = 0
        deleted_cars: list[str] = []

        if scope == "all":
            out_tree = _discover_folder_tree(output_dir, is_review=False)
            rev_tree = _discover_folder_tree(review_dir, is_review=True)
            all_cids = sorted(set(out_tree.keys()) | set(rev_tree.keys()))
            for cid in all_cids:
                deleted_photos += _delete_entire_car_group(cid)
                deleted_cars.append(cid)
            _save_json_dict(cars_meta_file, {})
            _save_json_dict(decisions_file, {})
        elif scope == "car":
            cids: list[str] = []
            if "car_ids" in payload and isinstance(payload["car_ids"], list):
                cids.extend(str(c) for c in payload["car_ids"] if c)
            if "car_id" in payload and payload["car_id"]:
                cids.append(str(payload["car_id"]))
            for cid in sorted(set(cids)):
                deleted_photos += _delete_entire_car_group(cid)
                deleted_cars.append(cid)
        else:
            items = payload.get("items", [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("car_id") and item.get("filename"):
                        deleted_photos += _delete_single_photo_files(
                            str(item["car_id"]), str(item["filename"])
                        )

        logger.info(
            "Delete action scope=%s removed %d photos (cars=%s) by %s",
            scope,
            deleted_photos,
            deleted_cars,
            user,
        )
        return JSONResponse(
            content={
                "ok": True,
                "scope": scope,
                "deleted_photos": deleted_photos,
                "deleted_cars": deleted_cars,
            }
        )

    def _find_original_bgr(car_id: str, filename: str) -> np.ndarray | None:
        """Find the original (before plate cover) BGR vehicle image for manual plate calibration."""
        safe_car = _validate_path_segment(car_id)
        safe_name = _validate_path_segment(filename)
        stem = Path(safe_name).stem

        search_dirs = [
            inbox_dir if safe_car == "_root" else (inbox_dir / safe_car),
            review_dir if safe_car == "_root" else (review_dir / safe_car),
            Path(paths_cfg.get("input_dir", "data/test_photos")),
            output_dir if safe_car == "_root" else (output_dir / safe_car),
        ]
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            exact = sdir / safe_name
            if exact.is_file():
                return load_image_bgr(exact)
            for ext in supported_exts:
                cand = sdir / f"{stem}{ext}"
                if cand.is_file():
                    return load_image_bgr(cand)
        return None

    def _resolve_covered_bgr_for_frame(
        car_id: str | None,
        filename: str | None,
        custom_quad_pct: list[list[float]] | None = None,
        remove_plate_cover: bool = False,
    ) -> np.ndarray:
        """Resolve the vehicle image for Frame Template Editor (with optional manual 4-corner quad or plate cover removed)."""
        if car_id and filename and remove_plate_cover:
            orig_bgr = _find_original_bgr(car_id, filename)
            if orig_bgr is not None:
                return orig_bgr

        if car_id and filename and custom_quad_pct and len(custom_quad_pct) == 4 and overlay_bgra is not None:
            orig_bgr = _find_original_bgr(car_id, filename)
            if orig_bgr is not None:
                img_h, img_w = orig_bgr.shape[:2]
                pts = np.array(
                    [[p[0] * img_w / 100.0, p[1] * img_h / 100.0] for p in custom_quad_pct],
                    dtype=np.float32,
                )
                feather_px = int(settings.get("overlay", {}).get("feather_px", 5))
                return warp_and_composite_single(
                    orig_bgr, overlay_bgra, pts, feather_px=feather_px
                )

        if car_id and filename:
            safe_car = _validate_path_segment(car_id)
            safe_name = _validate_path_segment(filename)
            stem = Path(safe_name).stem
            covered = _find_plate_covered_base(safe_car, stem)
            if covered is not None:
                return covered
            for base_d in (output_dir, review_dir):
                target_d = base_d if safe_car == "_root" else (base_d / safe_car)
                cand = target_d / safe_name
                if cand.is_file():
                    bgr = load_image_bgr(cand)
                    dets = _get_detector().detect_array(bgr, min_conf=low_conf_floor)
                    if dets:
                        return apply_plate_overlays(bgr, dets, settings, overlay_bgra).image_bgr
                    return bgr

        # Fallback to first available car photo in output_dir or data/test_photos
        out_tree = _discover_folder_tree(output_dir, is_review=False)
        for cid, items in out_tree.items():
            if items:
                first_f = items[0]["filename"]
                covered = _find_plate_covered_base(cid, Path(first_f).stem)
                if covered is not None:
                    return covered
                cand = (output_dir if cid == "_root" else (output_dir / cid)) / first_f
                if cand.is_file():
                    return load_image_bgr(cand)

        sample_candidates = list_supported_images(
            Path(paths_cfg.get("input_dir", "data/test_photos")), supported_exts
        )
        if sample_candidates:
            sample_bgr = load_image_bgr(sample_candidates[0])
            dets = _get_detector().detect_array(sample_bgr, min_conf=low_conf_floor)
            if dets:
                return apply_plate_overlays(sample_bgr, dets, settings, overlay_bgra).image_bgr
            return sample_bgr

        return np.full((720, 1280, 3), (225, 230, 238), dtype=np.uint8)

    @app.get("/api/plate-quad/{car_id}/{filename}")
    def api_get_plate_quad(
        car_id: str,
        filename: str,
        _user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Return initial 4-corner plate coordinates (in 0..100% of original image) for interactive adjustment."""
        orig_bgr = _find_original_bgr(car_id, filename)
        if orig_bgr is None:
            raise HTTPException(status_code=404, detail="Vehicle photo not found.")

        img_h, img_w = orig_bgr.shape[:2]
        dets = _get_detector().detect_array(orig_bgr, min_conf=low_conf_floor)
        if dets:
            best = max(dets, key=lambda d: d.confidence)
            quad_px, mode = estimate_plate_corners(orig_bgr, best.bbox, settings.get("overlay", {}))
            quad_pct = [
                [round(float(pt[0]) * 100.0 / img_w, 2), round(float(pt[1]) * 100.0 / img_h, 2)]
                for pt in quad_px
            ]
        else:
            # Default centered lower-bumper rectangle so user can drag it onto the plate
            quad_pct = [[36.0, 62.0], [64.0, 62.0], [64.0, 74.0], [36.0, 74.0]]
            mode = "manual_default"

        return JSONResponse(
            content={
                "ok": True,
                "car_id": car_id,
                "filename": filename,
                "mode": mode,
                "quad_pct": quad_pct,
            }
        )

    @app.get("/api/frame-render")
    def api_frame_render(
        car_id: str | None = Query(default=None),
        filename: str | None = Query(default=None),
        ratio: str = Query("1:1"),
        fit_mode: str = Query("fit"),
        template_style: str = Query("clean_white"),
        offset_x: float = Query(0.5),
        offset_y: float = Query(0.5),
        caption: int = Query(1),
        car_model: str = Query(""),
        car_price: str = Query(""),
        car_specs: str = Query(""),
        quad: str | None = Query(default=None),
        no_overlay: int = Query(0),
        download: int = Query(0),
        _user: str = Depends(verify_auth),
    ) -> Response:
        """Render an Apple-style Frame Studio image (1:1, 16:9, 9:16; Fit with blur vs Fill with pan; 5 templates)."""
        parsed_quad: list[list[float]] | None = None
        if quad and not no_overlay:
            try:
                nums = [float(x) for x in quad.split(",") if x.strip()]
                if len(nums) == 8:
                    parsed_quad = [
                        [nums[0], nums[1]],
                        [nums[2], nums[3]],
                        [nums[4], nums[5]],
                        [nums[6], nums[7]],
                    ]
            except ValueError:
                parsed_quad = None

        bgr = _resolve_covered_bgr_for_frame(
            car_id,
            filename,
            custom_quad_pct=parsed_quad,
            remove_plate_cover=bool(no_overlay),
        )
        rendered_pil = render_apple_frame_studio(
            image_bgr=bgr,
            ratio=ratio,
            fit_mode=fit_mode,
            template_style=template_style,
            offset_x=offset_x,
            offset_y=offset_y,
            caption_enabled=bool(caption),
            car_model=car_model,
            car_price=car_price,
            car_specs=car_specs,
        )
        max_w = 0 if download else 1080
        jpeg_bytes = _pil_to_jpeg_bytes(rendered_pil, max_width=max_w, quality=jpeg_quality)
        headers = {"Cache-Control": "private, no-store"}
        if download:
            safe_c = _sanitize_car_id(car_id or "Showroom")
            r_slug = ratio.replace(":", "x")
            headers["Content-Disposition"] = (
                f'attachment; filename="{safe_c}_{template_style}_{r_slug}.jpg"'
            )
        return Response(content=jpeg_bytes, media_type="image/jpeg", headers=headers)

    @app.post("/api/frame-save")
    def api_frame_save(
        payload: dict[str, Any] = Body(...),
        user: str = Depends(verify_auth),
    ) -> JSONResponse:
        """Apply adjusted plate cover (or remove plate cover) + frame and save/approve one or multiple photos into Gallery."""
        raw_cid = str(payload.get("car_id") or "FW-STUDIO")
        safe_car = _validate_path_segment(raw_cid) if raw_cid == "_root" else _sanitize_car_id(raw_cid)
        filename = str(payload.get("filename") or "studio.jpg")
        raw_filenames = payload.get("filenames")
        if isinstance(raw_filenames, list) and len(raw_filenames) > 0:
            target_filenames = [str(f) for f in raw_filenames if str(f).strip()]
        else:
            target_filenames = [filename]

        ratio = str(payload.get("ratio") or "1:1")
        fit_mode = str(payload.get("fit_mode") or "fit")
        template_style = str(payload.get("template_style") or "clean_white")
        offset_x = float(payload.get("offset_x", 0.5))
        offset_y = float(payload.get("offset_y", 0.5))
        caption_enabled = bool(payload.get("caption", True))
        car_model = str(payload.get("car_model") or "")
        car_price = str(payload.get("car_price") or "")
        car_specs = str(payload.get("car_specs") or "")
        quad_pct = payload.get("quad_pct") if isinstance(payload.get("quad_pct"), list) else None
        in_place = bool(payload.get("in_place", False))
        remove_plate_cover = bool(payload.get("remove_plate_cover", False))

        # Keep the global Frame configuration synced with the active Frames page setup
        cur_fcfg = _get_frame_config()
        _save_json_dict(
            frame_config_file,
            {
                "ratio": ratio,
                "fit_mode": fit_mode,
                "template_style": template_style,
                "offset_x": offset_x,
                "offset_y": offset_y,
                "caption_enabled": caption_enabled,
                "car_model": car_model or cur_fcfg["car_model"],
                "car_price": car_price,
                "car_specs": car_specs or cur_fcfg["car_specs"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        target_dir = output_dir if safe_car == "_root" else (output_dir / safe_car)
        target_dir.mkdir(parents=True, exist_ok=True)
        r_slug = ratio.replace(":", "x")

        saved_filenames: list[str] = []
        approved_count = 0
        last_out_path = ""
        decisions = _load_json_dict(decisions_file)
        decisions_changed = False

        for fname in target_filenames:
            safe_fname = _validate_path_segment(fname)
            # Only apply custom 4-corner quad to the active photo when saving a single photo (or when not removing plate cover)
            use_quad = quad_pct if (not remove_plate_cover and len(target_filenames) == 1 and safe_fname == filename) else None

            bgr = _resolve_covered_bgr_for_frame(
                safe_car,
                safe_fname,
                custom_quad_pct=use_quad,
                remove_plate_cover=remove_plate_cover,
            )
            rendered_pil = render_apple_frame_studio(
                image_bgr=bgr,
                ratio=ratio,
                fit_mode=fit_mode,
                template_style=template_style,
                offset_x=offset_x,
                offset_y=offset_y,
                caption_enabled=caption_enabled,
                car_model=car_model,
                car_price=car_price,
                car_specs=car_specs,
            )

            stem = Path(safe_fname).stem
            rev_candidate = (review_dir if safe_car == "_root" else (review_dir / safe_car)) / safe_fname
            was_in_review = rev_candidate.is_file()

            if was_in_review or in_place or len(target_filenames) > 1 or remove_plate_cover:
                out_name = f"{stem}.jpg"
            else:
                out_name = f"{stem}_frame_{template_style}_{r_slug}.jpg"

            out_path = target_dir / out_name
            rendered_pil.convert("RGB").save(out_path, format="JPEG", quality=jpeg_quality)

            # Update cached base image (either with plate cover or with plate cover removed)
            cache_f = output_dir / "_covered_cache" / safe_car / f"{Path(out_name).stem}.jpg"
            cache_f.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(cache_f), bgr)

            if was_in_review:
                rev_candidate.unlink(missing_ok=True)
                key = f"{safe_car}/{safe_fname}"
                decisions[key] = {
                    "status": "approved",
                    "approved_by": user,
                    "ratio": ratio,
                    "plate_cover_removed": remove_plate_cover,
                    "output_path": str(out_path),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                decisions_changed = True
                approved_count += 1
                logger.info("Approved review item from Frame Studio %s -> %s (by %s)", key, out_path, user)

            saved_filenames.append(out_name)
            last_out_path = str(out_path)

        if decisions_changed:
            _save_json_dict(decisions_file, decisions)

        return JSONResponse(
            content={
                "ok": True,
                "car_id": safe_car,
                "saved_filename": saved_filenames[-1] if saved_filenames else filename,
                "saved_filenames": saved_filenames,
                "processed_count": len(saved_filenames),
                "approved_count": approved_count,
                "approved_from_review": approved_count > 0,
                "plate_cover_removed": remove_plate_cover,
                "output_path": last_out_path,
            }
        )

    return app
