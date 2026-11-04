# Forest Wheel Photo Pipeline

Internal photo processing pipeline for **Forest Wheel** (Singapore used car dealership). Automatically detects license plates on raw vehicle photos, hides them with a branded overlay, and composes the result into standardized website or social media templates.

## Features (Phases 1–3)
- **Phase 1 — Plate Detection (`fwphotos.detect`)**: CPU-only YOLO inference (`ultralytics`), automatic downscaling for large images with coordinate rescaling, and support for JPEG, PNG, and HEIC (`pillow-heif`).
- **Phase 2 — Branded Plate Overlay (`fwphotos.overlay`)**: Quadrilateral corner detection within each bounding box, perspective transform (`cv2.getPerspectiveTransform`), soft edge feathering, and automatic axis-aligned fallback if corner detection is uncertain.
- **Phase 3 — Template Composition & Fail-Safe Pipeline (`fwphotos.compose`, `fwphotos.pipeline`)**: Places the covered car photo onto a configurable canvas (`website` 1600x1200 or `social_4_5` 1080x1350) with border, logo, and optional text fields. Enforces the strict **no plate, no publish** fail-safe rule and tracks processed files idempotently.

## Setup

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Ubuntu / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

## Usage

### 1. Detect Only (Debug & Model Evaluation)
Runs detection on a folder, saves annotated bounding-box images to `data/debug`, and prints a CSV summary (`filename,plate_count,max_confidence`):

```bash
python -m fwphotos.cli detect --input data/test_photos --debug data/debug
```

### 2. Full Pipeline Run
Runs detection, plate overlay, and template composition. Images with at least one covered plate at or above the confidence threshold are written to `data/output/`. Any image with no detection, low confidence, or an error is routed safely to `data/review/` with a logged reason:

```bash
python -m fwphotos.cli run --input data/test_photos --output data/output --review data/review
```

### 3. Tests
```bash
pytest -q
```

## Pretrained Model & Asset Licenses

| Component | Source | License | Notes |
| :--- | :--- | :--- | :--- |
| **License Plate YOLO Weights** (`models/plate_yolov8n.pt`) | Hugging Face: [`Koushim/yolov8-license-plate-detection`](https://huggingface.co/Koushim/yolov8-license-plate-detection) (`best.pt`) | **MIT License** (weights card) / **AGPL-3.0** (`ultralytics` runtime framework) | Fine-tuned YOLOv8n single-class (`license_plate`) detector. Weights are downloaded on first run to `models/` (gitignored). |
| **Brand Assets** (`assets/plate_overlay.png`, `assets/logo.png`) | Forest Wheel internal / generated placeholder assets | Proprietary / Internal Use (CC0 for synthetic placeholder) | Replace placeholders in `assets/` with production Forest Wheel graphics as needed. |
| **Fonts** (`assets/fonts/`) | DejaVu Sans / System Fallback | Bitstream Vera / Arev License (Permissive) | Configurable in `config/template.yaml`. |

