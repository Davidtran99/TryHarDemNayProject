import os
import time
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, "..", ".env"))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "corsheaders",
    "rest_framework",
    "hue_portal.core",
    "hue_portal.chatbot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "hue_portal.core.middleware.SecurityHeadersMiddleware",
    "hue_portal.core.middleware.AuditLogMiddleware",
]

ROOT_URLCONF = "hue_portal.hue_portal.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hue_portal.hue_portal.wsgi.application"

def _mask(value: str) -> str:
    if not value:
        return ""
    return value[:4] + "***"

database_url = env("DATABASE_URL", default=None)

if database_url:
    DATABASES = {"default": env.db("DATABASE_URL")}
    masked = database_url.replace(env("POSTGRES_PASSWORD", default=""), "***")
    print(f"[DB] Using DATABASE_URL: {masked}", flush=True)
else:
    print("[DB] DATABASE_URL not provided – thử kết nối qua POSTGRES_* / tunnel.", flush=True)
    try:
        import psycopg2

        host = env("POSTGRES_HOST", default="localhost")
        port = env("POSTGRES_PORT", default="5543")
        user = env("POSTGRES_USER", default="hue")
        password = env("POSTGRES_PASSWORD", default="huepass123")
        database = env("POSTGRES_DB", default="hue_portal")

        last_error = None
        for attempt in range(1, 4):
            try:
                test_conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    connect_timeout=3,
                )
                test_conn.close()
                last_error = None
                break
            except psycopg2.OperationalError as exc:
                last_error = exc
                print(
                    f"[DB] Attempt {attempt}/3 failed to reach PostgreSQL ({exc}).",
                    flush=True,
                )
                time.sleep(1)

        if last_error:
            raise last_error

        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": database,
                "USER": user,
                "PASSWORD": password,
                "HOST": host,
                "PORT": port,
            }
        }
        print(
            f"[DB] Connected to PostgreSQL at {host}:{port} as {_mask(user)}",
            flush=True,
        )
    except Exception as db_error:
        print(
            f"[DB] ⚠️ Falling back to SQLite because PostgreSQL is unavailable ({db_error})",
            flush=True,
        )
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }


# Cache configuration: opt-in Redis, otherwise safe local cache
USE_REDIS_CACHE = env.bool("ENABLE_REDIS_CACHE", default=False)
_redis_configured = False

if USE_REDIS_CACHE:
    try:
        import redis
        from urllib.parse import urlparse

        redis_url = env("REDIS_URL", default="redis://localhost:6380/0")
        parsed = urlparse(redis_url)
        test_client = redis.Redis(
            host=parsed.hostname or "localhost",
            port=parsed.port or 6380,
            username=parsed.username,
            password=parsed.password,
            db=int(parsed.path.lstrip("/") or 0),
            socket_connect_timeout=1,
        )
        test_client.ping()
        test_client.close()

        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": redis_url,
            }
        }
        _redis_configured = True
        print(f"[CACHE] ✅ Using Redis cache at {redis_url}", flush=True)
    except Exception as redis_error:
        print(f"[CACHE] ⚠️ Redis unavailable ({redis_error}), falling back to local cache.", flush=True)

if not _redis_configured:
    # LocMemCache keeps throttling functional without external services
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "hue-portal-default-cache",
        }
    }
    # Reduce throttling aggressiveness failures by ensuring predictable cache
    print("[CACHE] ℹ️ Using in-memory cache (LocMemCache).", flush=True)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
    },
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)  # Allow all in dev
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["*"]

SECURE_HSTS_SECONDS = 31536000
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

