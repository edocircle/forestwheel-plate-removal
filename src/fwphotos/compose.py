"""Template composition module for Forest Wheel listings and social media."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

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


def render_apple_frame_studio(
    image_bgr: np.ndarray,
    ratio: str = "1:1",
    fit_mode: str = "fit",
    template_style: str = "clean_white",
    offset_x: float = 0.5,
    offset_y: float = 0.5,
    caption_enabled: bool = True,
    car_model: str = "",
    car_price: str = "",
    car_specs: str = "",
) -> Image.Image:
    """Render a car photo inside the Apple-style Frame Template Editor.

    Args:
        image_bgr: Plate-covered vehicle image in BGR format.
        ratio: Aspect ratio ('1:1', '16:9', or '9:16').
        fit_mode:
          - 'fit' (Fit to frame): whole photo is visible, and empty space is filled
            with a blurred, enlarged copy of the same photo as background.
          - 'fill' (Fill frame): photo is cropped to cover the whole frame, with
            offset_x / offset_y (0.0 to 1.0) controlling pan/reposition.
        template_style: One of 'clean_white', 'soft_grey', 'minimal_border',
            'rounded_card', or 'glass_overlay'.
        offset_x: Horizontal crop centering (0.0 = left, 0.5 = center, 1.0 = right).
        offset_y: Vertical crop centering (0.0 = top, 0.5 = center, 1.0 = bottom).
        caption_enabled: Whether to render the optional model/price caption area.
        car_model: Vehicle title (e.g. '2023 Porsche 911 GT3').
        car_price: Vehicle price (e.g. '$248,900').
        car_specs: Optional subtitle/specs (e.g. '4,200 mi • PDK • Shark Blue').
    """
    r_clean = ratio.strip()
    if r_clean == "16:9":
        canvas_w, canvas_h = 1920, 1080
    elif r_clean == "9:16":
        canvas_w, canvas_h = 1080, 1920
    else:
        canvas_w, canvas_h = 1080, 1080

    style = template_style.strip().lower()
    mode = fit_mode.strip().lower()
    cx = max(0.0, min(1.0, float(offset_x)))
    cy = max(0.0, min(1.0, float(offset_y)))

    rgb_arr = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    photo_pil = Image.fromarray(rgb_arr)

    # Determine inner photo viewport and outer surface based on Apple template style
    caption_h = 116 if (caption_enabled and (car_model or car_price) and style in ("clean_white", "soft_grey", "rounded_card")) else 0

    if style == "clean_white":
        bg_color = (255, 255, 255)
        pad = 36
    elif style == "soft_grey":
        bg_color = (240, 237, 239)
        pad = 40
    elif style == "minimal_border":
        bg_color = (252, 248, 251)
        pad = 24
    elif style == "rounded_card":
        bg_color = (246, 243, 245)
        pad = 52
    else:
        # glass_overlay uses full-bleed canvas
        bg_color = (252, 248, 251)
        pad = 0

    canvas = Image.new("RGB", (canvas_w, canvas_h), bg_color)
    box_x1 = pad
    box_y1 = pad
    box_x2 = canvas_w - pad
    box_y2 = canvas_h - pad - caption_h
    box_w = max(1, box_x2 - box_x1)
    box_h = max(1, box_y2 - box_y1)

    # Build the photo viewport image according to fit_mode ("fit" vs "fill")
    if mode == "fill":
        viewport_img = ImageOps.fit(
            photo_pil,
            (box_w, box_h),
            method=Image.Resampling.LANCZOS,
            centering=(cx, cy),
        )
    else:
        # "Fit to frame": enlarged + Gaussian blurred copy of the same photo fills empty space
        blurred_bg = ImageOps.fit(
            photo_pil,
            (box_w, box_h),
            method=Image.Resampling.BILINEAR,
            centering=(0.5, 0.5),
        ).filter(ImageFilter.GaussianBlur(radius=32))
        # Slightly brighten/soften the blurred backdrop for Apple studio aesthetic
        soft_overlay = Image.new("RGB", (box_w, box_h), (255, 255, 255))
        viewport_img = Image.blend(blurred_bg, soft_overlay, alpha=0.14)

        contained = ImageOps.contain(
            photo_pil,
            (box_w, box_h),
            method=Image.Resampling.LANCZOS,
        )
        paste_x = (box_w - contained.width) // 2
        paste_y = (box_h - contained.height) // 2
        viewport_img.paste(contained, (paste_x, paste_y))

    # Apply rounded corners to viewport if style is rounded_card or clean_white/soft_grey
    if style in ("rounded_card", "clean_white", "soft_grey") and pad > 0:
        radius = 32 if style == "rounded_card" else 20
        mask = Image.new("L", (box_w, box_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=radius, fill=255)
        canvas.paste(viewport_img, (box_x1, box_y1), mask=mask)
    else:
        canvas.paste(viewport_img, (box_x1, box_y1))

    draw = ImageDraw.Draw(canvas, "RGBA")

    # Style-specific borders and overlays
    if style == "minimal_border":
        draw.rectangle(
            [pad, pad, canvas_w - 1 - pad, canvas_h - 1 - pad],
            outline=(27, 27, 29, 255),
            width=3,
        )
        draw.rectangle(
            [pad + 14, pad + 14, canvas_w - 1 - pad - 14, canvas_h - 1 - pad - 14],
            outline=(255, 255, 255, 190),
            width=2,
        )

    # Render optional caption (car model, specs, price)
    if caption_enabled and (car_model.strip() or car_price.strip()):
        title_font = _load_font(None, 32)
        sub_font = _load_font(None, 20)
        price_font = _load_font(None, 34)

        model_txt = car_model.strip()
        price_txt = car_price.strip()
        specs_txt = car_specs.strip() or "Forest Wheel Verified Showroom"

        if style in ("glass_overlay", "minimal_border"):
            # Floating frosted glass pill at the bottom of the frame
            bar_margin = 44
            bar_h = 112
            bar_y1 = canvas_h - bar_margin - bar_h
            bar_y2 = canvas_h - bar_margin
            bar_x1 = bar_margin
            bar_x2 = canvas_w - bar_margin

            draw.rounded_rectangle(
                [bar_x1, bar_y1, bar_x2, bar_y2],
                radius=24,
                fill=(255, 255, 255, 218),
                outline=(255, 255, 255, 245),
                width=2,
            )
            if model_txt:
                draw.text(
                    (bar_x1 + 28, bar_y1 + 22),
                    model_txt,
                    fill=(27, 27, 29, 255),
                    font=title_font,
                )
            if specs_txt:
                draw.text(
                    (bar_x1 + 28, bar_y1 + 64),
                    specs_txt,
                    fill=(65, 71, 85, 255),
                    font=sub_font,
                )
            if price_txt:
                try:
                    draw.text(
                        (bar_x2 - 28, bar_y1 + 56),
                        price_txt,
                        fill=(0, 88, 188, 255),
                        font=price_font,
                        anchor="rm",
                    )
                except ValueError:
                    draw.text(
                        (bar_x2 - 200, bar_y1 + 36),
                        price_txt,
                        fill=(0, 88, 188, 255),
                        font=price_font,
                    )
        else:
            # Clean studio footer below the photo
            footer_y = box_y2 + 20
            if model_txt:
                draw.text(
                    (box_x1 + 8, footer_y),
                    model_txt,
                    fill=(27, 27, 29, 255),
                    font=title_font,
                )
            if specs_txt:
                draw.text(
                    (box_x1 + 8, footer_y + 42),
                    specs_txt,
                    fill=(113, 119, 134, 255),
                    font=sub_font,
                )
            if price_txt:
                try:
                    draw.text(
                        (box_x2 - 8, footer_y + 34),
                        price_txt,
                        fill=(0, 88, 188, 255),
                        font=price_font,
                        anchor="rm",
                    )
                except ValueError:
                    draw.text(
                        (box_x2 - 180, footer_y + 16),
                        price_txt,
                        fill=(0, 88, 188, 255),
                        font=price_font,
                    )

    return canvas


