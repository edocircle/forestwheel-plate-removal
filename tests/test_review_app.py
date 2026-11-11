"""Unit tests for the Phase 5 FastAPI review web application."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from fwphotos.detect import Detection, PlateDetector
from fwphotos.review_app import create_review_app


class _ReviewStubDetector(PlateDetector):
    """Stub detector for review web app tests."""

    def __init__(self) -> None:
        super().__init__(weights_path=Path("models/dummy.pt"), confidence_threshold=0.40)

    def detect_array(
        self, image_bgr: np.ndarray, min_conf: float | None = None
    ) -> list[Detection]:
        return [Detection(bbox=(40, 40, 140, 80), confidence=0.35)]


def _setup_review_fixture(tmp_path: Path) -> tuple[TestClient, Path, Path, Path]:
    """Create a test review/ and output/ hierarchy with two cars in review/."""
    review_dir = tmp_path / "review"
    output_dir = tmp_path / "output"
    decisions_file = tmp_path / "review_decisions.json"
    state_file = tmp_path / "processed_state.json"

    car_dir = review_dir / "SBA8888X"
    car_dir.mkdir(parents=True)

    img1 = np.full((200, 300, 3), (60, 90, 140), dtype=np.uint8)
    cv2.imwrite(str(car_dir / "01_rear_angle.jpg"), img1)
    cv2.imwrite(str(car_dir / "02_interior.jpg"), img1)

    state_file.write_text(
        json.dumps(
            {
                "01_rear_angle.jpg": {"reason": "low_confidence (0.3500 < 0.4000)"},
                "02_interior.jpg": {"reason": "no_plate_detected"},
            }
        ),
        encoding="utf-8",
    )

    env = {
        "FW_REVIEW_USER": "reviewer",
        "FW_REVIEW_PASS": "s3cr3t-pass",
    }

    app = create_review_app(
        config_path=Path("config/settings.yaml"),
        review_dir_override=review_dir,
        output_dir_override=output_dir,
        decisions_file_override=decisions_file,
        state_file_override=state_file,
        detector=_ReviewStubDetector(),
        env=env,
    )
    return TestClient(app), review_dir, output_dir, decisions_file


def test_app_opens_directly_without_login_by_default(tmp_path: Path) -> None:
    """By default (require_auth=false), opening the app and its endpoints requires no login popup."""
    client, _, _, _ = _setup_review_fixture(tmp_path)

    resp_home = client.get("/")
    assert resp_home.status_code == 200
    assert "WWW-Authenticate" not in resp_home.headers

    resp_items = client.get("/api/items")
    assert resp_items.status_code == 200


def test_unauthenticated_requests_rejected_when_require_auth_enabled(tmp_path: Path) -> None:
    """When FW_REQUIRE_AUTH=1 is enabled, endpoints reject unauthenticated or wrong-password requests."""
    review_dir = tmp_path / "review_auth"
    output_dir = tmp_path / "output_auth"
    decisions_file = tmp_path / "decisions_auth.json"
    state_file = tmp_path / "state_auth.json"
    car_dir = review_dir / "SBA8888X"
    car_dir.mkdir(parents=True)
    img1 = np.full((200, 300, 3), (60, 90, 140), dtype=np.uint8)
    cv2.imwrite(str(car_dir / "01_rear_angle.jpg"), img1)
    cv2.imwrite(str(car_dir / "02_interior.jpg"), img1)
    state_file.write_text("{}", encoding="utf-8")

    app = create_review_app(
        config_path=Path("config/settings.yaml"),
        review_dir_override=review_dir,
        output_dir_override=output_dir,
        decisions_file_override=decisions_file,
        state_file_override=state_file,
        detector=_ReviewStubDetector(),
        env={"FW_REVIEW_USER": "reviewer", "FW_REVIEW_PASS": "s3cr3t-pass", "FW_REQUIRE_AUTH": "1"},
    )
    client = TestClient(app)

    endpoints = [
        ("GET", "/"),
        ("GET", "/api/items"),
        ("GET", "/media/before/SBA8888X/01_rear_angle.jpg"),
        ("GET", "/media/after/SBA8888X/01_rear_angle.jpg"),
        ("POST", "/api/approve/SBA8888X/01_rear_angle.jpg"),
        ("POST", "/api/reject/SBA8888X/02_interior.jpg"),
    ]
    for method, url in endpoints:
        # No credentials
        resp_no_auth = client.request(method, url)
        assert resp_no_auth.status_code == 401
        assert "Basic" in resp_no_auth.headers.get("WWW-Authenticate", "")

        # Wrong password
        resp_bad_auth = client.request(method, url, auth=("reviewer", "wrong"))
        assert resp_bad_auth.status_code == 401


def test_authenticated_dashboard_and_before_after_thumbnails(tmp_path: Path) -> None:
    """Authenticated user sees car cards, logged reasons, and valid JPEG before/after thumbnails."""
    client, _, _, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    resp = client.get("/", auth=auth)
    assert resp.status_code == 200
    assert "SBA8888X" in resp.text
    assert "01_rear_angle.jpg" in resp.text
    assert "low_confidence (0.3500 < 0.4000)" in resp.text
    assert "no_plate_detected" in resp.text

    before_resp = client.get("/media/before/SBA8888X/01_rear_angle.jpg", auth=auth)
    assert before_resp.status_code == 200
    assert before_resp.headers["content-type"] == "image/jpeg"
    assert before_resp.content[:2] == b"\xff\xd8"  # JPEG magic bytes

    after_resp = client.get("/media/after/SBA8888X/01_rear_angle.jpg", auth=auth)
    assert after_resp.status_code == 200
    assert after_resp.headers["content-type"] == "image/jpeg"
    assert after_resp.content[:2] == b"\xff\xd8"


def test_approve_moves_to_output_and_reject_marks_rejected_in_review(
    tmp_path: Path,
) -> None:
    """Approve writes composed image to output/ and removes from review/; Reject keeps in review/ marked rejected."""
    client, review_dir, output_dir, decisions_file = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # 1. Approve 01_rear_angle.jpg
    app_resp = client.post("/api/approve/SBA8888X/01_rear_angle.jpg", auth=auth)
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "approved"

    # File moved from review/SBA8888X/01_rear_angle.jpg -> output/SBA8888X/01_rear_angle.jpg
    assert not (review_dir / "SBA8888X" / "01_rear_angle.jpg").exists()
    assert (output_dir / "SBA8888X" / "01_rear_angle.jpg").exists()

    # 2. Reject 02_interior.jpg
    rej_resp = client.post("/api/reject/SBA8888X/02_interior.jpg", auth=auth)
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "rejected"

    # File stays in review/ and is marked rejected in decisions JSON and UI
    assert (review_dir / "SBA8888X" / "02_interior.jpg").exists()
    decisions = json.loads(decisions_file.read_text(encoding="utf-8"))
    assert decisions["SBA8888X/02_interior.jpg"]["status"] == "rejected"

    items_resp = client.get("/api/items", auth=auth).json()
    remaining = items_resp["cars"]["SBA8888X"]
    assert len(remaining) == 1
    assert remaining[0]["filename"] == "02_interior.jpg"
    assert remaining[0]["status"] == "rejected"


def test_multi_file_upload_and_aspect_ratio_crops(tmp_path: Path) -> None:
    """POST /api/upload processes multiple files and serves 1:1, 16:9, and 9:16 template crops."""
    client, _, output_dir, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # Create two synthetic JPEG images in memory
    img = np.full((240, 360, 3), (45, 90, 65), dtype=np.uint8)
    cv2.rectangle(img, (40, 40), (140, 80), (245, 245, 245), -1)
    _, jpg_buf = cv2.imencode(".jpg", img)
    jpg_bytes = jpg_buf.tobytes()

    # Use a high-confidence detector stub for upload
    class _HighConfDetector(PlateDetector):
        def __init__(self) -> None:
            super().__init__(weights_path=Path("models/dummy.pt"), confidence_threshold=0.40)

        def detect_array(
            self, image_bgr: np.ndarray, min_conf: float | None = None
        ) -> list[Detection]:
            return [Detection(bbox=(40, 40, 140, 80), confidence=0.95)]

    app = create_review_app(
        config_path=Path("config/settings.yaml"),
        review_dir_override=tmp_path / "review2",
        output_dir_override=output_dir,
        inbox_dir_override=tmp_path / "inbox2",
        decisions_file_override=tmp_path / "decisions2.json",
        state_file_override=tmp_path / "state2.json",
        detector=_HighConfDetector(),
        env={"FW_REVIEW_USER": "reviewer", "FW_REVIEW_PASS": "s3cr3t-pass"},
    )
    upload_client = TestClient(app)

    files = [
        ("files", ("front_view.jpg", jpg_bytes, "image/jpeg")),
        ("files", ("rear_view.jpg", jpg_bytes, "image/jpeg")),
    ]
    up_resp = upload_client.post(
        "/api/upload",
        data={"car_id": "FW-2026-GT3", "ratio": "16:9"},
        files=files,
        auth=auth,
    )
    assert up_resp.status_code == 200
    payload = up_resp.json()
    assert payload["car_id"] == "FW-2026-GT3"
    assert payload["processed_count"] == 2
    assert payload["output_count"] == 2

    # Verify 1:1, 16:9, and 9:16 crops can be fetched via /media/output/ and /api/export/
    for ratio in ("1:1", "16:9", "9:16"):
        media_resp = upload_client.get(
            f"/media/output/FW-2026-GT3/front_view.jpg?ratio={ratio}&download=1",
            auth=auth,
        )
        assert media_resp.status_code == 200
        assert media_resp.content[:2] == b"\xff\xd8"

    zip_resp = upload_client.get("/api/export/FW-2026-GT3?ratio=9:16", auth=auth)
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"


def test_apple_frame_studio_fit_blur_and_fill_templates(tmp_path: Path) -> None:
    """Verify Frame Template Editor renders 1:1, 16:9, 9:16 in Fit (blurred BG) & Fill modes across all 5 Apple templates."""
    client, _, output_dir, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # Approve one image so output/SBA8888X/01_rear_angle.jpg exists
    client.post("/api/approve/SBA8888X/01_rear_angle.jpg", auth=auth)

    for style in ("clean_white", "soft_grey", "minimal_border", "rounded_card", "glass_overlay"):
        for fit_mode in ("fit", "fill"):
            resp = client.get(
                f"/api/frame-render?car_id=SBA8888X&filename=01_rear_angle.jpg"
                f"&ratio=1:1&fit_mode={fit_mode}&template_style={style}"
                f"&offset_x=0.35&offset_y=0.65&caption=1&car_model=Porsche+911&car_price=$248,900",
                auth=auth,
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "image/jpeg"
            assert resp.content[:2] == b"\xff\xd8"

    # Save framed image to Gallery
    save_resp = client.post(
        "/api/frame-save",
        json={
            "car_id": "SBA8888X",
            "filename": "01_rear_angle.jpg",
            "ratio": "16:9",
            "fit_mode": "fit",
            "template_style": "rounded_card",
            "caption": True,
            "car_model": "2023 Porsche 911 GT3",
            "car_price": "$248,900",
        },
        auth=auth,
    )
    assert save_resp.status_code == 200
    saved_name = save_resp.json()["saved_filename"]
    assert (output_dir / "SBA8888X" / saved_name).exists()


def test_car_management_edit_and_delete_scopes(tmp_path: Path) -> None:
    """Verify editing car group metadata, single delete, multi-select delete, car group delete, and delete all."""
    client, review_dir, output_dir, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # Add a second car group in output_dir
    car2 = output_dir / "SXX1234A"
    car2.mkdir(parents=True)
    sample_img = np.full((180, 260, 3), (100, 120, 140), dtype=np.uint8)
    cv2.imwrite(str(car2 / "a.jpg"), sample_img)
    cv2.imwrite(str(car2 / "b.jpg"), sample_img)
    cv2.imwrite(str(car2 / "c.jpg"), sample_img)

    # 1. Edit car group metadata & rename SXX1234A -> SXX9999Z
    edit_resp = client.put(
        "/api/cars/SXX1234A",
        json={
            "new_car_id": "SXX9999Z",
            "plate_display": "SXX 9999 Z",
            "car_model": "BMW M3 Touring",
            "car_price": "$312,000",
        },
        auth=auth,
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["car_id"] == "SXX9999Z"
    assert (output_dir / "SXX9999Z" / "a.jpg").exists()

    # 2. Multi-select delete two photos (a.jpg and b.jpg)
    del_sel = client.post(
        "/api/delete",
        json={
            "scope": "selected",
            "items": [
                {"car_id": "SXX9999Z", "filename": "a.jpg"},
                {"car_id": "SXX9999Z", "filename": "b.jpg"},
            ],
        },
        auth=auth,
    )
    assert del_sel.status_code == 200
    assert del_sel.json()["deleted_photos"] == 2
    assert not (output_dir / "SXX9999Z" / "a.jpg").exists()
    assert (output_dir / "SXX9999Z" / "c.jpg").exists()

    # 3. Delete entire car group SXX9999Z
    del_car = client.post(
        "/api/delete",
        json={"scope": "car", "car_id": "SXX9999Z"},
        auth=auth,
    )
    assert del_car.status_code == 200
    assert not (output_dir / "SXX9999Z").exists()

    # 4. Delete all photos in inventory
    del_all = client.post(
        "/api/delete",
        json={"scope": "all"},
        auth=auth,
    )
    assert del_all.status_code == 200
    assert not (review_dir / "SBA8888X").exists()


def test_frame_config_preset_and_custom_plate_overlay(tmp_path: Path) -> None:
    """Verify saving Frame preset config applies to uploads/outputs and uploading a custom plate cover works."""
    client, _, output_dir, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # 1. Save global Frame configuration preset (Soft Grey, Fit to frame, 9:16)
    cfg_resp = client.post(
        "/api/frame-config",
        json={
            "ratio": "9:16",
            "fit_mode": "fit",
            "template_style": "soft_grey",
            "caption_enabled": True,
            "car_model": "Mercedes-AMG GT",
            "car_price": "$399,000",
        },
        auth=auth,
    )
    assert cfg_resp.status_code == 200
    saved_cfg = cfg_resp.json()["frame_config"]
    assert saved_cfg["ratio"] == "9:16"
    assert saved_cfg["template_style"] == "soft_grey"

    # 2. Upload a custom plate cover overlay image
    overlay_img = np.full((80, 260, 3), (10, 80, 200), dtype=np.uint8)
    _, png_buf = cv2.imencode(".png", overlay_img)
    ov_resp = client.post(
        "/api/plate-overlay",
        files=[("file", ("dealer_plate.png", png_buf.tobytes(), "image/png"))],
        auth=auth,
    )
    assert ov_resp.status_code == 200
    assert ov_resp.json()["has_custom_overlay"] is True

    # Serve active plate overlay
    get_ov = client.get("/media/plate-overlay", auth=auth)
    assert get_ov.status_code == 200
    assert get_ov.headers["content-type"] == "image/png"

    # 3. Approve review image and verify full-resolution popup endpoint works across ratios
    client.post("/api/approve/SBA8888X/01_rear_angle.jpg", auth=auth)
    full_resp = client.get(
        "/media/output/SBA8888X/01_rear_angle.jpg?ratio=9:16&full=1",
        auth=auth,
    )
    assert full_resp.status_code == 200
    assert full_resp.content[:2] == b"\xff\xd8"


def test_upload_empty_listing_price_hides_price_and_preserves_specs(tmp_path: Path) -> None:
    """When Listing Price is empty on Upload, car_price is stored as '' (no default price shown) and car_specs is saved."""
    _, _, output_dir, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    class _HighConfDetector(PlateDetector):
        def __init__(self) -> None:
            super().__init__(weights_path=Path("models/dummy.pt"), confidence_threshold=0.40)

        def detect_array(
            self, image_bgr: np.ndarray, min_conf: float | None = None
        ) -> list[Detection]:
            return [Detection(bbox=(40, 40, 140, 80), confidence=0.95)]

    app = create_review_app(
        config_path=Path("config/settings.yaml"),
        review_dir_override=tmp_path / "rev_empty_price",
        output_dir_override=output_dir,
        inbox_dir_override=tmp_path / "in_empty_price",
        decisions_file_override=tmp_path / "dec_empty_price.json",
        state_file_override=tmp_path / "st_empty_price.json",
        detector=_HighConfDetector(),
        env={"FW_REVIEW_USER": "reviewer", "FW_REVIEW_PASS": "s3cr3t-pass"},
    )
    client = TestClient(app)

    img = np.full((240, 360, 3), (45, 90, 65), dtype=np.uint8)
    _, jpg_buf = cv2.imencode(".jpg", img)

    up_resp = client.post(
        "/api/upload",
        data={
            "car_id": "SGP 9999 X",
            "ratio": "16:9",
            "car_model": "2024 Honda Civic Type R",
            "car_price": "",
            "car_specs": "Championship White • 6MT",
        },
        files=[("files", ("civic.jpg", jpg_buf.tobytes(), "image/jpeg"))],
        auth=auth,
    )
    assert up_resp.status_code == 200

    st_resp = client.get("/api/state", auth=auth).json()
    car_meta = st_resp["cars_meta"]["SGP-9999-X"]
    assert car_meta["car_price"] == ""
    assert car_meta["car_specs"] == "Championship White • 6MT"


def test_interactive_plate_quad_and_approve_from_frame_studio(tmp_path: Path) -> None:
    """Verify getting initial plate quad, live rendering with custom quad, and approving a review photo from Frame Studio."""
    client, review_dir, output_dir, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # 1. Fetch initial 4-corner plate coordinates for review photo
    quad_resp = client.get("/api/plate-quad/SBA8888X/01_rear_angle.jpg", auth=auth)
    assert quad_resp.status_code == 200
    qdata = quad_resp.json()
    assert qdata["ok"] is True
    assert len(qdata["quad_pct"]) == 4

    # 2. Preview render with user-adjusted tilted 4-corner coordinates
    render_resp = client.get(
        "/api/frame-render?car_id=SBA8888X&filename=01_rear_angle.jpg&ratio=1:1&quad=30,58,68,64,66,76,28,70",
        auth=auth,
    )
    assert render_resp.status_code == 200
    assert render_resp.content[:2] == b"\xff\xd8"

    # 3. Approve & Save from Frame Studio with custom quad_pct
    save_resp = client.post(
        "/api/frame-save",
        json={
            "car_id": "SBA8888X",
            "filename": "01_rear_angle.jpg",
            "ratio": "1:1",
            "fit_mode": "fit",
            "template_style": "clean_white",
            "caption": True,
            "car_model": "Porsche 911 GT3",
            "car_price": "",
            "car_specs": "PDK • Singapore",
            "in_place": True,
            "quad_pct": [[30.0, 58.0], [68.0, 64.0], [66.0, 76.0], [28.0, 70.0]],
        },
        auth=auth,
    )
    assert save_resp.status_code == 200
    sdata = save_resp.json()
    assert sdata["ok"] is True
    assert sdata["approved_from_review"] is True
    assert (output_dir / "SBA8888X" / "01_rear_angle.jpg").exists()
    assert not (review_dir / "SBA8888X" / "01_rear_angle.jpg").exists()


def test_multi_select_approve_and_remove_plate_cover_in_frame_studio(tmp_path: Path) -> None:
    """Verify multi-selecting photos in Frame Studio to remove plate cover and approve multiple images in one batch."""
    client, review_dir, output_dir, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # Add two more review photos (e.g., interior and side profile) to SBA8888X
    car_rev = review_dir / "SBA8888X"
    sample_img = np.full((240, 320, 3), (85, 110, 130), dtype=np.uint8)
    cv2.imwrite(str(car_rev / "02_interior_dash.jpg"), sample_img)
    cv2.imwrite(str(car_rev / "03_side_profile.jpg"), sample_img)

    # 1. Verify live preview with no_overlay=1 (Remove Plate Cover)
    no_ov_resp = client.get(
        "/api/frame-render?car_id=SBA8888X&filename=02_interior_dash.jpg&ratio=1:1&no_overlay=1",
        auth=auth,
    )
    assert no_ov_resp.status_code == 200
    assert no_ov_resp.content[:2] == b"\xff\xd8"

    # 2. Multi-select all 3 photos and click "Remove Plate Cover" (which also approves & saves them to Gallery)
    batch_resp = client.post(
        "/api/frame-save",
        json={
            "car_id": "SBA8888X",
            "filename": "01_rear_angle.jpg",
            "filenames": [
                "01_rear_angle.jpg",
                "02_interior_dash.jpg",
                "03_side_profile.jpg",
            ],
            "ratio": "16:9",
            "fit_mode": "fit",
            "template_style": "clean_white",
            "caption": True,
            "car_model": "Porsche 911 GT3",
            "car_price": "",
            "car_specs": "PDK • Singapore",
            "in_place": True,
            "remove_plate_cover": True,
        },
        auth=auth,
    )
    assert batch_resp.status_code == 200
    bdata = batch_resp.json()
    assert bdata["ok"] is True
    assert bdata["processed_count"] == 3
    assert bdata["approved_count"] == 3
    assert bdata["plate_cover_removed"] is True

    for fn in ("01_rear_angle.jpg", "02_interior_dash.jpg", "03_side_profile.jpg"):
        assert (output_dir / "SBA8888X" / fn).exists()
        assert not (review_dir / "SBA8888X" / fn).exists()


def test_gallery_export_zip_follows_frames_page_config(tmp_path: Path) -> None:
    """Verify Gallery ZIP download follows the 1:1 Fit to frame configuration set on the Frames page."""
    import io
    import zipfile
    from PIL import Image

    client, _, output_dir, _ = _setup_review_fixture(tmp_path)
    auth = ("reviewer", "s3cr3t-pass")

    # Configure Frames page to 1:1 Fit to frame
    cfg_resp = client.post(
        "/api/frame-config",
        json={
            "ratio": "1:1",
            "fit_mode": "fit",
            "template_style": "clean_white",
            "caption_enabled": True,
        },
        auth=auth,
    )
    assert cfg_resp.status_code == 200

    # Approve image into Gallery
    client.post("/api/approve/SBA8888X/01_rear_angle.jpg", auth=auth)

    # Download ZIP from Gallery without hardcoded 16:9 override
    zip_resp = client.get("/api/export/SBA8888X", auth=auth)
    assert zip_resp.status_code == 200
    assert "SBA8888X_1x1_export.zip" in zip_resp.headers.get("content-disposition", "")

    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
        names = zf.namelist()
        assert "01_rear_angle_1x1.jpg" in names
        with Image.open(io.BytesIO(zf.read("01_rear_angle_1x1.jpg"))) as exported_img:
            assert exported_img.size[0] == exported_img.size[1]


def test_user_profile_brand_logo_and_credentials_update(tmp_path: Path) -> None:
    """Verify editing dealership profile, uploading custom brand logo, rendering logo watermark, and changing login username/password."""
    client, _, _, _ = _setup_review_fixture(tmp_path)
    old_auth = ("reviewer", "s3cr3t-pass")

    # 1. Update dealership identity & enable logo watermark
    prof_resp = client.put(
        "/api/profile",
        json={
            "dealer_name": "Apex Motors SG",
            "dealer_tagline": "Luxury Showroom",
            "default_specs": "Agent Unit • Full Servicing",
            "currency_prefix": "SGD ",
            "show_logo_watermark": True,
        },
        auth=old_auth,
    )
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()["profile"]
    assert prof_data["dealer_name"] == "Apex Motors SG"
    assert prof_data["show_logo_watermark"] is True

    # 2. Upload custom brand logo
    logo_img = np.full((90, 220, 4), (30, 140, 250, 255), dtype=np.uint8)
    _, logo_buf = cv2.imencode(".png", logo_img)
    logo_up = client.post(
        "/api/profile/logo",
        files=[("file", ("apex_logo.png", logo_buf.tobytes(), "image/png"))],
        auth=old_auth,
    )
    assert logo_up.status_code == 200
    assert logo_up.json()["has_custom_logo"] is True

    # Serve active brand logo
    get_logo = client.get("/media/brand-logo", auth=old_auth)
    assert get_logo.status_code == 200
    assert get_logo.headers["content-type"] == "image/png"

    # Verify Frame Studio render succeeds with watermark enabled
    render_resp = client.get(
        "/api/frame-render?car_id=SBA8888X&filename=01_rear_angle.jpg&ratio=1:1",
        auth=old_auth,
    )
    assert render_resp.status_code == 200
    assert render_resp.content[:2] == b"\xff\xd8"

    # 3. Change username and password (wrong current_password must fail with 400)
    bad_cred = client.post(
        "/api/profile/credentials",
        json={
            "current_password": "wrong-password",
            "new_username": "apex_admin",
            "new_password": "new-strong-password",
            "confirm_password": "new-strong-password",
        },
        auth=old_auth,
    )
    assert bad_cred.status_code == 400

    # Valid credential update
    good_cred = client.post(
        "/api/profile/credentials",
        json={
            "current_password": "s3cr3t-pass",
            "new_username": "apex_admin",
            "new_password": "new-strong-password",
            "confirm_password": "new-strong-password",
        },
        auth=old_auth,
    )
    assert good_cred.status_code == 200
    assert good_cred.json()["username"] == "apex_admin"

    new_auth = ("apex_admin", "new-strong-password")
    new_prof_resp = client.get("/api/profile", auth=new_auth)
    assert new_prof_resp.status_code == 200
    assert new_prof_resp.json()["profile"]["username"] == "apex_admin"

    # Reset custom brand logo back to default
    del_logo = client.delete("/api/profile/logo", auth=new_auth)
    assert del_logo.status_code == 200
    assert del_logo.json()["has_custom_logo"] is False









