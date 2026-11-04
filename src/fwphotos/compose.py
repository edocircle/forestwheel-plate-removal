"""Template composition module for Forest Wheel listings and social media."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)


def load_template_config(
    template_path: Path = Path("config/template.yaml"),
) -> dict[str, Any]:
    """Load template configuration YAML from disk."""
    with template_path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _parse_rgb(color_val: str | list[int] | tuple[int, ...]) -> tuple[int, int, int]:
    """Parse hex string or RGB sequence into an (R, G, B) tuple."""
    if isinstance(color_val, str):
        return ImageColor.getrgb(color_val)[:3]
    return (int(color_val[0]), int(color_val[1]), int(color_val[2]))


def _load_font(font_path: str | None, font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load configured TrueType font or fall back cleanly to common system/default fonts."""
    candidates: list[str] = []
    if font_path:
        candidates.append(font_path)
    candidates.extend(
        [
            "assets/fonts/DejaVuSans-Bold.ttf",
            "DejaVuSans-Bold.ttf",
            "DejaVuSans.ttf",
            "arialbd.ttf",
            "arial.ttf",
        ]
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=font_size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_photo(
    photo_pil: Image.Image,
    target_w: int,
    target_h: int,
    fit_mode: str,
    bg_color: tuple[int, int, int],
) -> Image.Image:
    """Fit photo into (target_w, target_h) according to fit_mode ('cover', 'contain', 'stretch')."""
    mode = fit_mode.lower()
    if mode == "stretch":
        return photo_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if mode == "contain":
        contained = ImageOps.contain(
            photo_pil, (target_w, target_h), method=Image.Resampling.LANCZOS
        )
        box_canvas = Image.new("RGB", (target_w, target_h), bg_color)
        offset_x = (target_w - contained.width) // 2
        offset_y = (target_h - contained.height) // 2
        box_canvas.paste(contained, (offset_x, offset_y))
        return box_canvas
    # Default: "cover" (center-cropped aspect fill)
    return ImageOps.fit(
        photo_pil,
        (target_w, target_h),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )


def compose_template(
    image_bgr: np.ndarray,
    template_cfg: dict[str, Any],
    profile_name: str = "website",
) -> Image.Image:
    """Compose a BGR processed car image into the specified template profile."""
    profiles = template_cfg.get("profiles", {})
    if profile_name not in profiles:
        raise KeyError(
            f"Unknown template profile '{profile_name}'. Available: {list(profiles.keys())}"
        )

    prof = profiles[profile_name]
    canvas_w, canvas_h = (int(prof["canvas_size"][0]), int(prof["canvas_size"][1]))
    bg_rgb = _parse_rgb(prof.get("background_color", "#112219"))

    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_rgb)

    # 1. Place photo into target box
    photo_cfg = prof.get("photo", {})
    box = photo_cfg.get("box", [0, 0, canvas_w, canvas_h])
    px1, py1, px2, py2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
    box_w = max(1, px2 - px1)
    box_h = max(1, py2 - py1)
    fit_mode = str(photo_cfg.get("fit_mode", "cover"))
    photo_bg = _parse_rgb(photo_cfg.get("background_color", bg_rgb))

    rgb_arr = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    photo_pil = Image.fromarray(rgb_arr)
    fitted_photo = _fit_photo(photo_pil, box_w, box_h, fit_mode, photo_bg)
    canvas.paste(fitted_photo, (px1, py1))

    draw = ImageDraw.Draw(canvas)

    # 2. Draw border if enabled
    border_cfg = prof.get("border", {})
    if border_cfg.get("enabled", False):
        b_width = int(border_cfg.get("width", 8))
        b_inset = int(border_cfg.get("inset", 12))
        b_color = _parse_rgb(border_cfg.get("color", "#D4AF37"))
        draw.rectangle(
            [b_inset, b_inset, canvas_w - 1 - b_inset, canvas_h - 1 - b_inset],
            outline=b_color,
            width=b_width,
        )

    # 3. Paste logo if enabled
    logo_cfg = prof.get("logo", {})
    if logo_cfg.get("enabled", False):
        logo_path = Path(logo_cfg.get("path", "assets/logo.png"))
        if logo_path.exists():
            with Image.open(logo_path) as logo_img:
                logo_rgba = logo_img.convert("RGBA")
                max_size = logo_cfg.get("max_size")
                if max_size:
                    logo_rgba.thumbnail(
                        (int(max_size[0]), int(max_size[1])),
                        Image.Resampling.LANCZOS,
                    )
                lx, ly = int(logo_cfg["position"][0]), int(logo_cfg["position"][1])
                canvas.paste(logo_rgba, (lx, ly), mask=logo_rgba)
        else:
            logger.warning("Logo asset not found at %s; skipping logo.", logo_path)

    # 4. Render optional text fields
    for field in prof.get("text_fields", []):
        text_str = str(field.get("text", "")).strip()
        if not text_str:
            continue
        tx, ty = int(field["position"][0]), int(field["position"][1])
        font_size = int(field.get("font_size", 24))
        font_path = field.get("font_path") or None
        color = _parse_rgb(field.get("color", "#FFFFFF"))
        anchor = field.get("anchor")
        font = _load_font(font_path, font_size)

        try:
            if anchor:
                draw.text((tx, ty), text_str, fill=color, font=font, anchor=anchor)
            else:
                draw.text((tx, ty), text_str, fill=color, font=font)
        except ValueError:
            # Fallback if bitmap default font does not support anchor
            draw.text((tx, ty), text_str, fill=color, font=font)

    return canvas
