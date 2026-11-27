"""Settings for the Fallah & Sons store backend.

All deployment-specific values come from environment variables. See
`backend/.env.example` and `docs/DEPLOYMENT.md`.
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# "development" | "test" | "production"
STORE_ENV = env("STORE_ENV", "development")
IS_PRODUCTION = STORE_ENV == "production"

DEBUG = env_bool("DJANGO_DEBUG", not IS_PRODUCTION)
SECRET_KEY = env("DJANGO_SECRET_KEY") or ("dev-insecure-key-do-not-use-in-production" if not IS_PRODUCTION else None)
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required in production.")
if IS_PRODUCTION and DEBUG:
    raise ImproperlyConfigured("DEBUG must be False in production.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:3010,http://127.0.0.1:3010")

# Public origin of the storefront (used for payment callbacks and links in invoices).
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:3010").rstrip("/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "azbankgateways",
    "apps.core",
    "apps.catalog",
    "apps.accounts",
    "apps.shipping",
    "apps.orders",
    "apps.payments",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL URL.")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60")),
        "ATOMIC_REQUESTS": False,
    }


DATABASES = {
    "default": _database_from_url(env("DATABASE_URL", "postgres://fallah:fallah_dev_pw@127.0.0.1:55432/fallah"))
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa"
LANGUAGES = [("fa", "فارسی")]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = Path(env("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles")))
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Uploads: product photos are the largest expected files.
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
MAX_IMAGE_UPLOAD_BYTES = 8 * 1024 * 1024

# Sessions & cookies
SESSION_COOKIE_NAME = env("DJANGO_SESSION_COOKIE_NAME", "sessionid")
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", IS_PRODUCTION)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", IS_PRODUCTION)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Behind the reverse proxy (nginx in production, Next.js rewrites in development).
USE_X_FORWARDED_HOST = env_bool("DJANGO_USE_X_FORWARDED_HOST", True)
if env_bool("DJANGO_TRUST_X_FORWARDED_PROTO", IS_PRODUCTION):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)  # TLS terminates at the proxy
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", "0"))

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.core.authentication.CsrfEnforcedSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "apps.core.api.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.core.api.StorePagination",
    "PAGE_SIZE": 12,
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
    "DEFAULT_THROTTLE_RATES": {
        "cart": "120/min",
        "checkout": "10/min",
        "pay": "10/min",
        "track": "10/min",
        "otp": "10/min",
    },
    # Number of trusted reverse proxies in front of Django (nginx = 1). Used for client IPs.
    "NUM_PROXIES": int(env("DJANGO_NUM_PROXIES", "1" if IS_PRODUCTION else "0")) or None,
}
TRUST_X_REAL_IP = env_bool("DJANGO_TRUST_X_REAL_IP", IS_PRODUCTION)

# Database cache: shared across gunicorn workers for throttling, no Redis needed.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# --- Store business configuration -------------------------------------------------

# Minutes a checkout holds stock before the order expires if unpaid.
ORDER_RESERVATION_MINUTES = int(env("ORDER_RESERVATION_MINUTES", "30"))
# Sample (demo) products can be bought only outside production unless explicitly allowed.
STORE_ALLOW_SAMPLE_SALES = env_bool("STORE_ALLOW_SAMPLE_SALES", not IS_PRODUCTION)

# Next.js on-demand revalidation (best effort, catalog changes).
STOREFRONT_REVALIDATE_URL = env("STOREFRONT_REVALIDATE_URL", "http://127.0.0.1:3010/api/revalidate")
STOREFRONT_REVALIDATE_SECRET = env("STOREFRONT_REVALIDATE_SECRET", "dev-revalidate-secret")

# --- SMS / OTP -----------------------------------------------------------------------

SMS_BACKEND = env("SMS_BACKEND", "console" if not IS_PRODUCTION else "kavenegar")
KAVENEGAR_API_KEY = env("KAVENEGAR_API_KEY", "")
KAVENEGAR_OTP_TEMPLATE = env("KAVENEGAR_OTP_TEMPLATE", "")
OTP_TTL_SECONDS = 120
OTP_MAX_VERIFY_ATTEMPTS = 5
if IS_PRODUCTION and SMS_BACKEND == "console":
    raise ImproperlyConfigured("The console SMS backend cannot be used in production.")

# --- Payments --------------------------------------------------------------------------

# The development mock bank never contacts a real provider. It must never run in production.
PAYMENT_MOCK_ENABLED = env_bool("PAYMENT_MOCK_ENABLED", not IS_PRODUCTION)
if IS_PRODUCTION and PAYMENT_MOCK_ENABLED:
    raise ImproperlyConfigured("PAYMENT_MOCK_ENABLED must be False in production.")

_gateways: dict[str, dict] = {}
if env("ZARINPAL_MERCHANT_CODE"):
    _gateways["ZARINPAL"] = {
        "MERCHANT_CODE": env("ZARINPAL_MERCHANT_CODE"),
        "SANDBOX": int(env_bool("ZARINPAL_SANDBOX", False)),
    }
if env("ZIBAL_MERCHANT_CODE"):
    _gateways["ZIBAL"] = {"MERCHANT_CODE": env("ZIBAL_MERCHANT_CODE")}
if env("SEP_MERCHANT_CODE"):
    _gateways["SEP"] = {
        "MERCHANT_CODE": env("SEP_MERCHANT_CODE"),
        "TERMINAL_CODE": env("SEP_TERMINAL_CODE", env("SEP_MERCHANT_CODE")),
    }
if env("MELLAT_TERMINAL_CODE"):
    _gateways["MELLAT"] = {
        "TERMINAL_CODE": env("MELLAT_TERMINAL_CODE"),
        "USERNAME": env("MELLAT_USERNAME", ""),
        "PASSWORD": env("MELLAT_PASSWORD", ""),
    }
if env("BMI_MERCHANT_CODE"):
    _gateways["BMI"] = {
        "MERCHANT_CODE": env("BMI_MERCHANT_CODE"),
        "TERMINAL_CODE": env("BMI_TERMINAL_CODE", ""),
        "SECRET_KEY": env("BMI_SECRET_KEY", ""),
    }
if PAYMENT_MOCK_ENABLED:
    _gateways["MOCK"] = {}

AZ_IRANIAN_BANK_GATEWAYS = {
    "GATEWAYS": _gateways,
    "DEFAULT": env("PAYMENT_DEFAULT_PROVIDER", "MOCK" if PAYMENT_MOCK_ENABLED else "ZARINPAL"),
    # Canonical store currency: integer Iranian rial. The library handles gateway currency.
    "CURRENCY": "IRR",
    "TRACKING_CODE_QUERY_PARAM": "tc",
    "TRACKING_CODE_LENGTH": 16,
    "SETTING_VALUE_READER_CLASS": "azbankgateways.readers.DefaultReader",
    "BANK_PRIORITIES": [],
    # Return gateway url/params to our code instead of passing them through a GET redirect page.
    "IS_SAFE_GET_GATEWAY_PAYMENT": True,
    "IS_SAMPLE_FORM_ENABLE": False,
}

# The library reads its bank class map from a top-level setting named CLASS.
CLASS = {
    "BMI": "azbankgateways.banks.BMI",
    "SEP": "azbankgateways.banks.SEP",
    "ZARINPAL": "apps.payments.banks.Zarinpal",
    "ZIBAL": "azbankgateways.banks.Zibal",
    "BAHAMTA": "azbankgateways.banks.Bahamta",
    "MELLAT": "azbankgateways.banks.Mellat",
    "IRANDARGAH": "azbankgateways.banks.irandargah.IranDargah",
    "ASANPARDAKHT": "azbankgateways.banks.asanpardakht.AsanPardakht",
}
if PAYMENT_MOCK_ENABLED:
    CLASS["MOCK"] = "apps.payments.mock_bank.MockBank"

# --- Logging -----------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "apps.core.logging.RedactSecretsFilter"}},
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain", "filters": ["redact"]}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
    },
}
