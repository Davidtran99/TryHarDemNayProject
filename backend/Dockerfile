FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# System dependencies (OCR + build essentials)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
        libpoppler-cpp-dev \
        pkg-config \
        libgl1 && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app

CMD ["gunicorn", "-b", "0.0.0.0:8000", "hue_portal.hue_portal.wsgi:application"]

