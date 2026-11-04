\# AGENTS.md: Forest Wheel Photo Pipeline



\## Purpose

Internal tool for Forest Wheel (Singapore used car dealership). It takes raw car photos,

hides license plates with a branded overlay, and composes the photos into a standard

Forest Wheel template for website listings and social media.



\## Stack

\- Python 3.11+, virtualenv at `.venv`

\- ultralytics (YOLO) for plate detection, CPU-only inference

\- opencv-python for perspective transforms and compositing

\- Pillow (+ pillow-heif) for template composition and HEIC reading

\- PyYAML for config, pytest for tests

\- Later phases: watchdog, rclone (Google Drive sync), FastAPI or Streamlit (review UI), Caddy



\## Deployment target

Hetzner VPS (Ubuntu, small CPU-only instance, non-root user). Development happens in

Antigravity. Keep memory and CPU use modest: process images one at a time, resize large

images for inference, never load a whole batch into RAM.



\## Project structure

```

src/fwphotos/   detect.py, overlay.py, compose.py, pipeline.py, cli.py

config/         settings.yaml, template.yaml

assets/         plate\_overlay.png, logo.png, fonts/

tests/

data/           (gitignored) test\_photos/, debug/, output/, review/

```



\## Hard rules (never break these)

1\. \*\*Never modify or overwrite original photos.\*\* Read from the input folder, write only to

&#x20;  output/review/debug folders.

2\. \*\*Fail safe: no plate, no publish.\*\* An image only goes to `output/` if at least one plate

&#x20;  was detected at or above the confidence threshold AND it was covered. Anything else

&#x20;  (no detection, low confidence, overlay failure, any exception) goes to `review/` with a

&#x20;  reason in the log. Never silently pass through an uncovered image.

3\. \*\*Never run OCR or store plate numbers.\*\* We only need plate locations. Do not read,

&#x20;  log, or save plate text anywhere.

4\. \*\*Never commit\*\* photos, model weights, tokens, credentials, rclone config, or `.env`

&#x20;  files. Keep them in `.gitignore`.

5\. \*\*All tunable values live in config\*\*, not in code: confidence threshold, template

&#x20;  layout, fonts, colors, output sizes, folder paths, overlay padding.

6\. \*\*One bad image must not stop a batch.\*\* Catch per-image exceptions, log them, route the

&#x20;  image to `review/`, and continue.

7\. \*\*No new heavy dependencies\*\* (no GPU libraries, no large frameworks) without asking.

8\. \*\*Record the license\*\* of any pretrained model or asset used in the README.



\## Coding standards

\- Type hints on all functions, short docstrings, small single-purpose functions.

\- Use `pathlib`, `logging` (not print), and `argparse` for the CLI.

\- Every module gets at least one pytest test using small sample images in `tests/fixtures/`.

\- Deterministic, idempotent runs: re-running on the same input gives the same output and

&#x20; does not duplicate work.



\## Commands

\- Setup: `python -m venv .venv \&\& pip install -r requirements.txt`

\- Detect only (debug): `python -m fwphotos.cli detect --input data/test\_photos --debug data/debug`

\- Full run: `python -m fwphotos.cli run --input data/test\_photos --output data/output --review data/review`

\- Tests: `pytest -q`



\## Workflow

\- Work phase by phase. Do not start a later phase until the current phase's acceptance

&#x20; criteria are met and I confirm.

\- Before coding each phase, show a short plan. After coding, run the tests and show results.

\- Commit after each working step with a clear message.

\- If a requirement is ambiguous, ask instead of guessing.

