"""Google Drive rclone synchronization, folder readiness checks, and Telegram alerts."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fwphotos.detect import PlateDetector, list_supported_images, load_settings
from fwphotos.pipeline import ImageProcessRecord, run_pipeline

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CarSyncRecord:
    """Persistent record for a processed car folder."""

    car_id: str
    processed_at: str
    total_images: int
    output_count: int
    review_count: int
    status: str  # "completed" or "partial_review"


def send_telegram_alert(
    message: str,
    sync_cfg: dict[str, Any],
    env: dict[str, str] | None = None,
) -> bool:
    """Send an error notification via Telegram Bot API using env-provided credentials.

    Never raises an exception so alerting failures cannot crash the batch.
    """
    tg_cfg = sync_cfg.get("telegram", {})
    if not tg_cfg.get("enabled", True):
        return False

    environ = os.environ if env is None else env
    token_var = str(tg_cfg.get("bot_token_env", "FW_TELEGRAM_BOT_TOKEN"))
    chat_var = str(tg_cfg.get("chat_id_env", "FW_TELEGRAM_CHAT_ID"))
    timeout = int(tg_cfg.get("timeout_seconds", 10))

    bot_token = environ.get(token_var, "").strip()
    chat_id = environ.get(chat_var, "").strip()
    if not bot_token or not chat_id:
        logger.warning(
            "Telegram alert skipped: %s or %s environment variable is not set.",
            token_var,
            chat_var,
        )
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": f"[Forest Wheel Pipeline Alert]\n{message}"}
    ).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to send Telegram alert: %s", exc)
        return False


def build_remote_uri(remote_name: str, remote_subpath: str) -> str:
    """Format an rclone remote URI such as gdrive:Forest Wheel Inventory/inbox."""
    clean_remote = remote_name.rstrip(":")
    clean_path = remote_subpath.strip("/")
    return f"{clean_remote}:{clean_path}"


def build_rclone_exclude_args(
    video_extensions: list[str],
    processed_car_ids: set[str] | None = None,
) -> list[str]:
    """Build rclone --exclude arguments to skip video files and already-processed cars."""
    args: list[str] = []
    for ext in video_extensions:
        clean_ext = ext if ext.startswith(".") else f".{ext}"
        args.extend(["--exclude", f"*{clean_ext.lower()}"])
        args.extend(["--exclude", f"*{clean_ext.upper()}"])
    if processed_car_ids:
        for car_id in sorted(processed_car_ids):
            args.extend(["--exclude", f"{car_id}/**"])
    return args


def run_rclone_copy(
    source: str,
    destination: str,
    sync_cfg: dict[str, Any],
    extra_args: list[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    """Execute `rclone copy` between source and destination; raise RuntimeError on failure."""
    rclone_bin = str(sync_cfg.get("rclone_binary", "rclone"))
    timeout = int(sync_cfg.get("rclone_timeout_seconds", 600))

    cmd = [rclone_bin, "copy", source, destination]
    if extra_args:
        cmd.extend(extra_args)

    logger.info("Running rclone: %s", " ".join(cmd))
    result = runner(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        stderr_msg = (result.stderr or "").strip()
        raise RuntimeError(
            f"rclone copy failed (exit {result.returncode}): {stderr_msg}"
        )


def is_car_folder_ready(
    car_dir: Path,
    supported_extensions: list[str],
    video_extensions: list[str],
    ready_marker_file: str = "ready.txt",
    quiescence_seconds: float = 90.0,
    now_ts: float | None = None,
) -> tuple[bool, str]:
    """Determine if a car folder in local inbox is ready to be processed.

    Rule:
    1. Ready immediately if `<car_dir>/<ready_marker_file>` exists (and folder has >= 1 image).
    2. Otherwise ready if all non-video files in `<car_dir>` have been unchanged
       for at least `quiescence_seconds` (and folder has >= 1 supported image).
    """
    if not car_dir.exists() or not car_dir.is_dir():
        return False, "not_a_directory"

    images = list_supported_images(car_dir, supported_extensions)
    marker_path = car_dir / ready_marker_file
    if marker_path.is_file():
        if not images:
            return False, "ready_marker_present_but_no_supported_images"
        return True, "ready_marker"

    if not images:
        return False, "no_supported_images"

    video_ext_set = {e.lower() for e in video_extensions}
    non_video_files = [
        p
        for p in car_dir.rglob("*")
        if p.is_file() and p.suffix.lower() not in video_ext_set
    ]
    if not non_video_files:
        return False, "no_files"

    current_time = time.time() if now_ts is None else now_ts
    latest_mtime = max(p.stat().st_mtime for p in non_video_files)
    age_seconds = current_time - latest_mtime

    if age_seconds >= quiescence_seconds:
        return True, f"quiescent ({age_seconds:.1f}s >= {quiescence_seconds:.1f}s)"
    return False, f"waiting_for_quiescence ({age_seconds:.1f}s < {quiescence_seconds:.1f}s)"


def load_car_state(state_file: Path) -> dict[str, dict[str, Any]]:
    """Load processed car IDs state dictionary from JSON file."""
    if not state_file.exists():
        return {}
    try:
        with state_file.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read car state file %s: %s", state_file, exc)
        return {}


def save_car_state(state_file: Path, state: dict[str, dict[str, Any]]) -> None:
    """Persist processed car IDs state dictionary to JSON file."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)


def _has_files(folder: Path) -> bool:
    """Return True if folder exists and contains at least one file."""
    if not folder.exists():
        return False
    return any(p.is_file() for p in folder.rglob("*"))


def sync_once(
    config_path: Path = Path("config/settings.yaml"),
    detector: PlateDetector | None = None,
    rclone_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    now_ts: float | None = None,
    env: dict[str, str] | None = None,
) -> list[CarSyncRecord]:
    """Execute one full sync cycle: pull inbox -> check readiness -> run pipeline -> push results."""
    settings = load_settings(config_path)
    sync_cfg = settings.get("sync", {})
    det_cfg = settings.get("detection", {})

    remote_name = str(sync_cfg.get("remote_name", "gdrive"))
    remote_inbox = str(sync_cfg.get("remote_inbox", "Forest Wheel Inventory/inbox"))
    remote_processed = str(
        sync_cfg.get("remote_processed", "Forest Wheel Inventory/processed")
    )
    remote_review = str(sync_cfg.get("remote_review", "Forest Wheel Inventory/review"))

    local_inbox_dir = Path(sync_cfg.get("local_inbox_dir", "/srv/fw/inbox"))
    local_output_dir = Path(sync_cfg.get("local_output_dir", "/srv/fw/output"))
    local_review_dir = Path(sync_cfg.get("local_review_dir", "/srv/fw/review"))
    car_state_file = Path(
        sync_cfg.get("car_state_file", "/srv/fw/state/synced_cars.json")
    )

    ready_marker = str(sync_cfg.get("ready_marker_file", "ready.txt"))
    quiescence_sec = float(sync_cfg.get("quiescence_seconds", 90))
    supported_exts = list(
        det_cfg.get("supported_extensions", [".jpg", ".jpeg", ".png", ".heic"])
    )
    video_exts = list(
        sync_cfg.get(
            "skip_video_extensions",
            [".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".3gp"],
        )
    )

    local_inbox_dir.mkdir(parents=True, exist_ok=True)
    local_output_dir.mkdir(parents=True, exist_ok=True)
    local_review_dir.mkdir(parents=True, exist_ok=True)

    car_state = load_car_state(car_state_file)
    processed_car_ids = set(car_state.keys())

    # 1. Pull new car folders from gdrive:"Forest Wheel Inventory/inbox" to /srv/fw/inbox
    inbox_uri = build_remote_uri(remote_name, remote_inbox)
    exclude_args = build_rclone_exclude_args(video_exts, processed_car_ids)
    try:
        run_rclone_copy(
            source=inbox_uri,
            destination=str(local_inbox_dir),
            sync_cfg=sync_cfg,
            extra_args=exclude_args,
            runner=rclone_runner,
        )
    except Exception as exc:  # noqa: BLE001
        err_msg = f"Failed pulling inbox from {inbox_uri}: {exc}"
        logger.error(err_msg)
        send_telegram_alert(err_msg, sync_cfg, env=env)
        raise

    # 2. Discover candidate car folders in /srv/fw/inbox
    car_folders = sorted(
        [p for p in local_inbox_dir.iterdir() if p.is_dir()],
        key=lambda p: p.name.lower(),
    )

    completed_records: list[CarSyncRecord] = []

    for car_dir in car_folders:
        car_id = car_dir.name
        if car_id in processed_car_ids:
            logger.debug("Skipping already-processed car folder: %s", car_id)
            continue

        ready, reason = is_car_folder_ready(
            car_dir=car_dir,
            supported_extensions=supported_exts,
            video_extensions=video_exts,
            ready_marker_file=ready_marker,
            quiescence_seconds=quiescence_sec,
            now_ts=now_ts,
        )
        if not ready:
            logger.info("Car folder %s not ready yet (%s); skipping this cycle.", car_id, reason)
            continue

        logger.info("Processing ready car folder %s (%s)...", car_id, reason)
        car_out_dir = local_output_dir / car_id
        car_rev_dir = local_review_dir / car_id
        car_img_state = car_state_file.parent / f"images_{car_id}.json"

        try:
            if detector is None:
                detector = PlateDetector.from_config(settings)

            img_records: list[ImageProcessRecord] = run_pipeline(
                input_dir=car_dir,
                output_dir=car_out_dir,
                review_dir=car_rev_dir,
                config_path=config_path,
                state_file=car_img_state,
                detector=detector,
            )

            # Check if any image suffered an unexpected exception during detection/processing
            error_records = [
                r
                for r in img_records
                if r.destination == "review"
                and r.reason.startswith(("detection_error", "processing_error", "hash_error"))
            ]
            if error_records:
                details = "; ".join(f"{r.filename}: {r.reason}" for r in error_records)
                send_telegram_alert(
                    f"Pipeline error(s) in car '{car_id}': {details}",
                    sync_cfg,
                    env=env,
                )

            # 4. Copy results back to gdrive:"Forest Wheel Inventory/processed/<car-id>"
            #    and gdrive:"Forest Wheel Inventory/review/<car-id>"
            if _has_files(car_out_dir):
                dest_proc_uri = build_remote_uri(
                    remote_name, f"{remote_processed}/{car_id}"
                )
                run_rclone_copy(
                    source=str(car_out_dir),
                    destination=dest_proc_uri,
                    sync_cfg=sync_cfg,
                    extra_args=build_rclone_exclude_args(video_exts),
                    runner=rclone_runner,
                )

            if _has_files(car_rev_dir):
                dest_rev_uri = build_remote_uri(
                    remote_name, f"{remote_review}/{car_id}"
                )
                run_rclone_copy(
                    source=str(car_rev_dir),
                    destination=dest_rev_uri,
                    sync_cfg=sync_cfg,
                    extra_args=build_rclone_exclude_args(video_exts),
                    runner=rclone_runner,
                )

            out_count = sum(1 for r in img_records if r.destination == "output")
            rev_count = sum(1 for r in img_records if r.destination == "review")
            status = "completed" if rev_count == 0 else "partial_review"

            car_rec = CarSyncRecord(
                car_id=car_id,
                processed_at=datetime.now(timezone.utc).isoformat(),
                total_images=len(img_records),
                output_count=out_count,
                review_count=rev_count,
                status=status,
            )
            car_state[car_id] = asdict(car_rec)
            save_car_state(car_state_file, car_state)
            processed_car_ids.add(car_id)
            completed_records.append(car_rec)
            logger.info(
                "Finished car_id=%s | total=%d | output=%d | review=%d | status=%s",
                car_id,
                car_rec.total_images,
                out_count,
                rev_count,
                status,
            )

        except Exception as exc:  # noqa: BLE001
            err_msg = f"Error syncing/processing car '{car_id}': {exc}"
            logger.error(err_msg)
            send_telegram_alert(err_msg, sync_cfg, env=env)
            continue

    return completed_records

