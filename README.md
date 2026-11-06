# Fake Image Checker

A Django prototype for exploring image authenticity signals. It combines local checks (metadata, error-level analysis, and visual artifacts) with an optional vision-model review through OpenRouter.

**Important:** The result is a heuristic assessment, not proof that an image is genuine, edited, or AI-generated. Scores should not be used for high-stakes decisions.

## What it does

- Accepts JPG, PNG, and WEBP uploads.
- Checks file metadata and basic image-level signals.
- Optionally asks a vision model to describe suspicious details.
- Combines the checks into a result with reasons and individual scores.
- Stores previous analyses in SQLite and provides a history page.

## Tech stack

Python, Django, SQLite, Pillow, OpenCV, NumPy, and OpenRouter API.

## Run locally

Use Python 3.11 or 3.12 with the pinned dependencies below. Clone the repository, open a terminal in the project folder, and create a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and configure `OPENROUTER_API_KEY` if you want the external vision-model step. Without a key, the application reports that the model check is unavailable.

Set up the database and start Django:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

Uploads are limited to 10 MiB and 20 million pixels by default. Set
`MAX_UPLOAD_SIZE_MB` and `MAX_UPLOAD_PIXELS` in `.env` to adjust these limits.
The form verifies the actual image format and decodes pixels before saving;
damaged images and Pillow decompression-bomb warnings are rejected.

## Checks and tests

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

GitHub Actions runs these checks on Python 3.11 and 3.12. Tests cover score
normalization, API-failure scoring fallback, and image upload validation using
generated images. They do not call OpenRouter or measure detection accuracy.

## Main routes

| Route | Purpose |
| --- | --- |
| `/` | Upload an image |
| `/check/` | Process a submitted image (POST) |
| `/result/<id>/` | Show an analysis result |
| `/history/` | View recent analyses |
| `/admin/` | Django administration |

## How the analysis works

1. Django validates and saves the uploaded file.
2. Local analysis extracts metadata and calculates image heuristics.
3. If configured, the server sends the image to the OpenRouter model.
4. The scoring module combines the results and stores an explanation in SQLite.

Most of the application logic lives under `detector/services/`; request handling is in `detector/views.py`.

## Current limitations

- No independently validated accuracy benchmark; displayed probabilities are estimates, not calibrated measurements.
- Image-processing techniques such as ELA can be misleading after resizing or recompression.
- Uploaded images and results are stored locally. The history endpoint is not access-controlled in this prototype; do not use it with private images or deploy it publicly as-is.
- The default Django settings are intended for local development, not production.
- Tests cover scoring and uploads; access-control and external API integration tests and a deployment-ready configuration remain future work.

## Next improvements

- Add tests for upstream parsing failures and non-finite score values.
- Protect analysis history and set a retention policy for uploads.
- Remove the legacy API-key-file fallback and harden production settings.
- Publish sample results using non-sensitive images and document false positives.

This repository is a learning project and a working prototype, not a forensic verification service.
