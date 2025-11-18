# Celery Worker Operations Guide

Celery handles the ingestion queue (`IngestionJob`). Every environment must run at least one worker alongside the Django web app.

## Local (Docker Compose)

```bash
POSTGRES_EXPOSE_PORT=5543 \
REDIS_EXPOSE_PORT=6380 \
docker compose up -d db redis
docker compose up celery web
```

The `celery` service in `docker-compose.yml` already runs `celery -A hue_portal.hue_portal worker -l info`. Logs can be tailed via:

```bash
docker compose logs -f celery
```

## macOS/Linux (venv)

```bash
cd backend/hue_portal
source ../.venv/bin/activate
export CELERY_TASK_ALWAYS_EAGER=false
export REDIS_URL=redis://localhost:6379/0
celery -A hue_portal.hue_portal worker -l info
```

## Procfile (Heroku / Render)

```
web: gunicorn hue_portal.hue_portal.wsgi:application --bind 0.0.0.0:8000
worker: celery -A hue_portal.hue_portal worker -l info --concurrency=2
```

## systemd Service (Ubuntu)

`/etc/systemd/system/celery.service`

```
[Unit]
Description=Celery Worker
After=network.target

[Service]
User=deploy
WorkingDirectory=/var/app/current/backend/hue_portal
EnvironmentFile=/var/app/current/.env
ExecStart=/var/app/current/.venv/bin/celery -A hue_portal.hue_portal worker -l info --concurrency=4
Restart=always

[Install]
WantedBy=multi-user.target
```

Reload + enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now celery
sudo systemctl status celery
```

## Health Verification

1. Start worker + redis.
2. Upload a DOCX via `/legal-upload`.
3. Call `GET /api/legal-ingestion-jobs/<job_id>/` → status should transition `pending → running → completed`.
4. Investigate failures with `docker compose logs celery` (or `journalctl -u celery`).

