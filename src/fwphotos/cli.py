"""Command-line interface for Forest Wheel photo pipeline."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

from fwphotos.detect import (
    PlateDetector,
    list_supported_images,
    load_image_bgr,
    load_settings,
    save_debug_image,
)

logger = logging.getLogger("fwphotos")


def configure_logging(verbose: bool = False) -> None:
    """Configure application logging to stderr."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


def cmd_detect(args: argparse.Namespace) -> int:
    """Run plate detection on a folder, save annotated debug copies, and output CSV summary."""
    settings = load_settings(Path(args.config))
    paths_cfg = settings.get("paths", {})
    det_cfg = settings.get("detection", {})

    input_dir = Path(args.input or paths_cfg.get("input_dir", "data/test_photos"))
    debug_dir = Path(args.debug or paths_cfg.get("debug_dir", "data/debug"))
    extensions = det_cfg.get("supported_extensions", [".jpg", ".jpeg", ".png", ".heic"])

    detector = PlateDetector.from_config(settings)
    image_paths = list_supported_images(input_dir, extensions)

    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["filename", "plate_count", "max_confidence"])

    for img_path in image_paths:
        try:
            image_bgr = load_image_bgr(img_path)
            detections = detector.detect_array(image_bgr)
            debug_out = debug_dir / f"{img_path.stem}_debug.jpg"
            save_debug_image(image_bgr, detections, debug_out)

            plate_count = len(detections)
            max_conf = max((d.confidence for d in detections), default=0.0)
            writer.writerow([img_path.name, plate_count, f"{max_conf:.4f}"])
            logger.info(
                "Detected %s: plate_count=%d, max_confidence=%.4f -> %s",
                img_path.name,
                plate_count,
                max_conf,
                debug_out,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Error detecting plates in %s: %s", img_path.name, exc)
            writer.writerow([img_path.name, 0, "0.0000"])

    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Execute full detection, overlay, and composition pipeline on a folder."""
    from fwphotos.pipeline import run_pipeline

    settings = load_settings(Path(args.config))
    paths_cfg = settings.get("paths", {})

    input_dir = Path(args.input or paths_cfg.get("input_dir", "data/test_photos"))
    output_dir = Path(args.output or paths_cfg.get("output_dir", "data/output"))
    review_dir = Path(args.review or paths_cfg.get("review_dir", "data/review"))
    state_file = (
        Path(args.state_file)
        if getattr(args, "state_file", None)
        else Path(paths_cfg.get("state_file", "data/processed_state.json"))
    )

    run_pipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        review_dir=review_dir,
        config_path=Path(args.config),
        state_file=state_file,
        profile=getattr(args, "profile", None),
        force=getattr(args, "force", False),
    )
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Execute one Google Drive rclone sync and per-car processing cycle."""
    from fwphotos.sync import sync_once

    try:
        sync_once(config_path=Path(args.config))
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.error("Sync cycle failed: %s", exc)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fwphotos",
        description="Forest Wheel license plate overlay and template composition tool",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings YAML file (default: config/settings.yaml)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser(
        "detect",
        help="Run plate detection on a folder, save annotated debug images, and print CSV",
    )
    detect_parser.add_argument(
        "--input", required=False, help="Input directory containing raw photos"
    )
    detect_parser.add_argument(
        "--debug", required=False, help="Output directory for annotated debug images"
    )
    detect_parser.set_defaults(func=cmd_detect)

    run_parser = subparsers.add_parser(
        "run",
        help="Run full pipeline (detect -> overlay -> compose) with fail-safe routing",
    )
    run_parser.add_argument(
        "--input", required=False, help="Input directory containing raw photos"
    )
    run_parser.add_argument(
        "--output", required=False, help="Output directory for finished template images"
    )
    run_parser.add_argument(
        "--review", required=False, help="Review directory for uncertain or failed images"
    )
    run_parser.add_argument(
        "--state-file",
        required=False,
        help="Path to idempotency state JSON file",
    )
    run_parser.add_argument(
        "--profile",
        required=False,
        choices=["website", "social_4_5"],
        help="Override template output profile (website or social_4_5)",
    )
    run_parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process images even if already recorded in state file",
    )
    run_parser.set_defaults(func=cmd_run)

    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync car folders from Google Drive via rclone, run pipeline on ready cars, and push results",
    )
    sync_parser.set_defaults(func=cmd_sync)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

