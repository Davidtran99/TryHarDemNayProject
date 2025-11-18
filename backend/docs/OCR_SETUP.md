# Tesseract OCR Runtime Setup

PyMuPDF + `pytesseract` require the native **tesseract-ocr** binary (with Vietnamese language data) to extract text from scanned PDFs. Install it on every environment that runs ingestion or Celery workers.

## Docker / CI (Debian-based)

The backend Dockerfile already installs the required packages:

```bash
apt-get update && apt-get install -y \
  tesseract-ocr \
  tesseract-ocr-eng \
  tesseract-ocr-vie
```

For GitHub Actions or other CI images, run the same command before executing tests that touch OCR.

## macOS (Homebrew)

```bash
brew install tesseract
brew install tesseract-lang # optional (contains vie)
```

Verify:

```bash
tesseract --version
ls /opt/homebrew/Cellar/tesseract/*/share/tessdata/vie.traineddata
```

## Ubuntu / Debian

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-vie
```

## Rocky / CentOS (DNF)

```bash
sudo dnf install -y tesseract tesseract-langpack-eng tesseract-langpack-vie
```

## Configuration

- Set `OCR_LANGS` (default `vie+eng`) if additional language combinations are needed.
- `OCR_PDF_ZOOM` (default `2.0`) controls rasterization DPI; increase for very small fonts.
- Check that `tesseract` is in `$PATH` for the user running Django/Celery.

## Troubleshooting

1. Run `tesseract --list-langs` to confirm Vietnamese appears.
2. Ensure the worker container/user has read access to `/usr/share/tesseract-ocr/4.00/tessdata`.
3. If OCR still fails, set `CELERY_TASK_ALWAYS_EAGER=true` locally to debug synchronously and inspect logs for `pytesseract` errors.

