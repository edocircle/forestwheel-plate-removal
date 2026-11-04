"""FastAPI web application for reviewing uncertain car photos (mobile & iPad friendly)."""

from __future__ import annotations

import html
import io
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
from fastapi import Depends, FastAPI, HTTPException, Response, status
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
from fwphotos.overlay import apply_plate_overlays, load_overlay_rgba

logger = logging.getLogger(__name__)
security = HTTPBasic(auto_error=False)


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


def _resolve_review_file(review_dir: Path, car_id: str, filename: str) -> Path:
    """Resolve and verify a file inside review_dir."""
    safe_car = _validate_path_segment(car_id)
    safe_name = _validate_path_segment(filename)

    if safe_car == "_root":
        candidate = (review_dir / safe_name).resolve()
    else:
        candidate = (review_dir / safe_car / safe_name).resolve()

    base_resolved = review_dir.resolve()
    if base_resolved not in candidate.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path."
        )
    if not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review image not found."
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
    low_conf_floor: float = 0.05,
) -> Image.Image:
    """Generate the 'After' composed image (covering any detected low-conf plates if present)."""
    image_bgr = load_image_bgr(img_path)
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

    profile_name = str(settings.get("output", {}).get("active_profile", "website"))
    return compose_template(processed_bgr, template_cfg, profile_name=profile_name)


def _pil_to_jpeg_bytes(pil_img: Image.Image, max_width: int, quality: int = 85) -> bytes:
    """Resize PIL image to thumbnail width and encode as JPEG bytes."""
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
    decisions_file_override: Path | None = None,
    state_file_override: Path | None = None,
    detector: PlateDetector | None = None,
    env: dict[str, str] | None = None,
) -> FastAPI:
    """Create and configure the FastAPI review application."""
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
    decisions_file = Path(
        decisions_file_override
        or app_cfg.get("decisions_file", "data/review_decisions.json")
    )
    state_file = Path(
        state_file_override or paths_cfg.get("state_file", "data/processed_state.json")
    )
    car_state_file_cfg = sync_cfg.get("car_state_file")
    car_state_dir = Path(car_state_file_cfg).parent if car_state_file_cfg else None

    template_path = Path(paths_cfg.get("template_config", "config/template.yaml"))
    template_cfg = load_template_config(template_path)

    overlay_path = Path(
        paths_cfg.get("plate_overlay_asset", "assets/plate_overlay.png")
    )
    overlay_bgra = load_overlay_rgba(overlay_path) if overlay_path.exists() else None

    supported_exts = list(
        det_cfg.get("supported_extensions", [".jpg", ".jpeg", ".png", ".heic"])
    )
    thumb_width = int(app_cfg.get("thumbnail_width", 640))
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
        title="Forest Wheel Review Queue",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    def _discover_cars_in_review() -> dict[str, list[dict[str, Any]]]:
        """Group review images by car folder (or '_root' for flat files in review_dir)."""
        decisions = _load_json_dict(decisions_file)
        grouped: dict[str, list[dict[str, Any]]] = {}
        if not review_dir.exists():
            return grouped

        # 1. Direct images in review_dir (_root)
        root_imgs = list_supported_images(review_dir, supported_exts)
        if root_imgs:
            grouped["_root"] = []
            for p in root_imgs:
                key = f"_root/{p.name}"
                dec = decisions.get(key, {})
                grouped["_root"].append(
                    {
                        "car_id": "_root",
                        "filename": p.name,
                        "reason": _lookup_logged_reason(
                            "_root", p.name, state_file, car_state_dir
                        ),
                        "status": dec.get("status", "pending"),
                        "updated_at": dec.get("updated_at", ""),
                    }
                )

        # 2. Per-car subfolders in review_dir/<car-id>
        subfolders = sorted(
            [d for d in review_dir.iterdir() if d.is_dir()],
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
                        "reason": _lookup_logged_reason(
                            cid, p.name, state_file, car_state_dir
                        ),
                        "status": dec.get("status", "pending"),
                        "updated_at": dec.get("updated_at", ""),
                    }
                )
        return grouped

    @app.get("/", response_class=HTMLResponse)
    def index(_user: str = Depends(verify_auth)) -> HTMLResponse:
        """Render mobile & iPad friendly HTML review interface."""
        grouped = _discover_cars_in_review()
        html_body = _render_dashboard_html(grouped)
        return HTMLResponse(content=html_body)

    @app.get("/api/items")
    def api_list_items(_user: str = Depends(verify_auth)) -> JSONResponse:
        """Return JSON list of cars and images currently in review/."""
        return JSONResponse(content={"cars": _discover_cars_in_review()})

    @app.get("/media/before/{car_id}/{filename}")
    def media_before(
        car_id: str, filename: str, _user: str = Depends(verify_auth)
    ) -> Response:
        """Serve authenticated 'Before' thumbnail of a review image."""
        img_path = _resolve_review_file(review_dir, car_id, filename)
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
        car_id: str, filename: str, _user: str = Depends(verify_auth)
    ) -> Response:
        """Serve authenticated 'After' template preview thumbnail of a review image."""
        img_path = _resolve_review_file(review_dir, car_id, filename)
        composed_pil = _render_composed_image(
            img_path=img_path,
            settings=settings,
            template_cfg=template_cfg,
            detector=_get_detector(),
            overlay_bgra=overlay_bgra,
            low_conf_floor=low_conf_floor,
        )
        jpeg_bytes = _pil_to_jpeg_bytes(composed_pil, max_width=thumb_width)
        return Response(
            content=jpeg_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.post("/api/approve/{car_id}/{filename}")
    def api_approve(
        car_id: str, filename: str, user: str = Depends(verify_auth)
    ) -> JSONResponse:
        """Approve a review image: compose template, write to output/, remove from review/."""
        img_path = _resolve_review_file(review_dir, car_id, filename)
        composed_pil = _render_composed_image(
            img_path=img_path,
            settings=settings,
            template_cfg=template_cfg,
            detector=_get_detector(),
            overlay_bgra=overlay_bgra,
            low_conf_floor=low_conf_floor,
        )

        target_dir = output_dir if car_id == "_root" else (output_dir / car_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{img_path.stem}.jpg"
        composed_pil.save(out_path, format="JPEG", quality=jpeg_quality)

        # Remove from review/ now that it has moved to output/
        img_path.unlink()

        decisions = _load_json_dict(decisions_file)
        key = f"{car_id}/{filename}"
        decisions[key] = {
            "status": "approved",
            "approved_by": user,
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
        _resolve_review_file(review_dir, car_id, filename)
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


def _render_dashboard_html(grouped: dict[str, list[dict[str, Any]]]) -> str:
    """Render responsive HTML5 page tailored for mobile and iPad screens."""
    total_items = sum(len(items) for items in grouped.values())
    sections_html: list[str] = []

    if not grouped:
        sections_html.append(
            '<div class="empty-state"><h2>No photos pending in review/</h2>'
            "<p>All processed car folders are clear.</p></div>"
        )
    else:
        for car_id, items in grouped.items():
            display_car = "General Review Queue" if car_id == "_root" else f"Car: {html.escape(car_id)}"
            cards: list[str] = []
            for item in items:
                fname = item["filename"]
                reason = html.escape(item["reason"])
                st = item["status"]
                safe_cid_url = html.escape(car_id)
                safe_fname_url = html.escape(fname)
                card_id = f"card-{html.escape(car_id)}-{html.escape(fname)}".replace(".", "-")

                badge_cls = "badge-rejected" if st == "rejected" else "badge-pending"
                badge_txt = "REJECTED" if st == "rejected" else "NEEDS REVIEW"

                cards.append(
                    f"""
                <article class="review-card {'is-rejected' if st == 'rejected' else ''}" id="{card_id}">
                  <header class="card-header">
                    <div>
                      <span class="filename">{html.escape(fname)}</span>
                      <span class="reason-pill">Reason: {reason}</span>
                    </div>
                    <span class="status-badge {badge_cls}" id="{card_id}-badge">{badge_txt}</span>
                  </header>
                  <div class="thumbs-grid">
                    <figure class="thumb-box">
                      <figcaption>BEFORE (Original in review/)</figcaption>
                      <img loading="lazy" src="/media/before/{safe_cid_url}/{safe_fname_url}" alt="Before {html.escape(fname)}" />
                    </figure>
                    <figure class="thumb-box">
                      <figcaption>AFTER (Template Preview)</figcaption>
                      <img loading="lazy" src="/media/after/{safe_cid_url}/{safe_fname_url}" alt="After {html.escape(fname)}" />
                    </figure>
                  </div>
                  <footer class="card-actions">
                    <button type="button" class="btn btn-approve"
                      onclick="handleDecision('{safe_cid_url}', '{safe_fname_url}', 'approve', '{card_id}')">
                      ✓ Approve &amp; Move to Output
                    </button>
                    <button type="button" class="btn btn-reject"
                      onclick="handleDecision('{safe_cid_url}', '{safe_fname_url}', 'reject', '{card_id}')">
                      ✕ Reject (Keep in Review)
                    </button>
                  </footer>
                </article>
                """
                )

            sections_html.append(
                f"""
            <section class="car-section">
              <h2 class="car-title">{display_car} <span class="count-pill">{len(items)} photo(s)</span></h2>
              <div class="cards-list">
                {''.join(cards)}
              </div>
            </section>
            """
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Forest Wheel — Photo Review Queue</title>
  <style>
    :root {{
      --bg: #0d1b14;
      --surface: #15291f;
      --border: #2a4738;
      --gold: #d4af37;
      --text: #f3f6f4;
      --muted: #a7bdb1;
      --green-btn: #238636;
      --red-btn: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      padding-bottom: 3rem;
    }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      background: #09130e;
      border-bottom: 2px solid var(--gold);
      padding: 0.9rem 1.25rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .topbar h1 {{
      margin: 0;
      font-size: 1.15rem;
      letter-spacing: 0.04em;
      color: var(--gold);
    }}
    .container {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 1rem;
    }}
    .car-section {{
      margin-bottom: 2rem;
    }}
    .car-title {{
      font-size: 1.2rem;
      border-left: 4px solid var(--gold);
      padding-left: 0.75rem;
      margin: 1rem 0;
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}
    .count-pill {{
      font-size: 0.8rem;
      background: var(--border);
      padding: 0.2rem 0.6rem;
      border-radius: 999px;
      color: var(--muted);
    }}
    .review-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem;
      margin-bottom: 1.25rem;
      box-shadow: 0 4px 14px rgba(0,0,0,0.3);
    }}
    .review-card.is-rejected {{
      border-color: var(--red-btn);
      opacity: 0.82;
    }}
    .card-header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.85rem;
    }}
    .filename {{
      font-weight: 700;
      font-size: 1rem;
      margin-right: 0.5rem;
    }}
    .reason-pill {{
      display: inline-block;
      background: #2b2111;
      color: #facc15;
      border: 1px solid #854d0e;
      padding: 0.2rem 0.55rem;
      border-radius: 6px;
      font-size: 0.82rem;
    }}
    .status-badge {{
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
    }}
    .badge-pending {{ background: #1e3a2f; color: #86efac; }}
    .badge-rejected {{ background: #451a1a; color: #fca5a5; }}
    .thumbs-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.85rem;
    }}
    @media (max-width: 720px) {{
      .thumbs-grid {{ grid-template-columns: 1fr; }}
    }}
    .thumb-box {{
      margin: 0;
      background: #0a140f;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }}
    .thumb-box figcaption {{
      font-size: 0.78rem;
      color: var(--muted);
      padding: 0.45rem 0.65rem;
      border-bottom: 1px solid var(--border);
      font-weight: 600;
    }}
    .thumb-box img {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .card-actions {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
      margin-top: 1rem;
    }}
    .btn {{
      min-height: 48px;
      border: none;
      border-radius: 8px;
      font-size: 0.98rem;
      font-weight: 700;
      color: #fff;
      cursor: pointer;
      touch-action: manipulation;
    }}
    .btn-approve {{ background: var(--green-btn); }}
    .btn-reject {{ background: var(--red-btn); }}
    .btn:active {{ transform: scale(0.99); }}
    .empty-state {{
      text-align: center;
      padding: 3rem 1rem;
      background: var(--surface);
      border-radius: 12px;
      border: 1px solid var(--border);
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <h1>FOREST WHEEL • PHOTO REVIEW</h1>
    <span>{total_items} item(s) in review</span>
  </header>
  <main class="container">
    {''.join(sections_html)}
  </main>
  <script>
    async function handleDecision(carId, filename, action, cardId) {{
      const url = `/api/${{action}}/${{encodeURIComponent(carId)}}/${{encodeURIComponent(filename)}}`;
      const card = document.getElementById(cardId);
      const badge = document.getElementById(cardId + '-badge');
      try {{
        const resp = await fetch(url, {{ method: 'POST' }});
        if (!resp.ok) {{
          alert('Action failed: ' + resp.statusText);
          return;
        }}
        if (action === 'approve') {{
          card.style.transition = 'opacity 0.25s ease';
          card.style.opacity = '0';
          setTimeout(() => card.remove(), 260);
        }} else {{
          card.classList.add('is-rejected');
          if (badge) {{
            badge.textContent = 'REJECTED';
            badge.className = 'status-badge badge-rejected';
          }}
        }}
      }} catch (err) {{
        alert('Network error: ' + err);
      }}
    }}
  </script>
</body>
</html>"""
