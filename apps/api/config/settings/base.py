from __future__ import annotations

import base64
import hashlib
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parents[2]


def env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


def env_optional(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key, default)
    if value is None:
        return None
    value = value.strip()
    return value or None


def env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = env("DJANGO_SECRET_KEY", "django-insecure-corpershub-dev-key")
DEBUG = env_bool("DJANGO_DEBUG", False)
#ALLOWED_HOSTS = [host.strip() for host in env("DJANGO_ALLOWED_HOSTS", "*").split(",") if host.strip()]
ALLOWED_HOSTS = os.environ["DJANGO_ALLOWED_HOSTS"].split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "corsheaders",
    "storages",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "channels",
    "apps.common",
    "apps.audit",
    "apps.accounts",
    "apps.companies.apps.CompaniesConfig",
    "apps.corpers",
    "apps.search",
    "apps.interests",
    "apps.chat",
    "apps.payments",
    "apps.subscriptions",
    "apps.notifications",
    "apps.verification",
    "apps.adminpanel",
]

MIDDLEWARE = [
    "apps.common.middleware.HealthCheckCommonMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "corpershub"),
        "USER": env("POSTGRES_USER", "corpershub"),
        "PASSWORD": env("POSTGRES_PASSWORD", "corpershub"),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Africa/Lagos")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.accounts.authentication.CorpersJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": "120/minute",
        "anon": "30/minute",
        "auth_login": "10/minute",
        "auth_otp": "6/minute",
        "password_reset_request": "5/hour",
        "password_reset_verify": "10/minute",
        "password_reset_complete": "10/minute",
        "company_lookup": "12/minute",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "corpershub API",
    "DESCRIPTION": "API for companies, NYSC corps members, and internal operators.",
    "VERSION": "1.0.0",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", "14"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL_ORIGINS", True)
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in env("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
CORS_ALLOW_CREDENTIALS = env_bool("CORS_ALLOW_CREDENTIALS", True)
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in env("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]

AUTH_REFRESH_COOKIE_NAME = env("AUTH_REFRESH_COOKIE_NAME", "corpershub_refresh")
AUTH_REFRESH_COOKIE_PATH = env("AUTH_REFRESH_COOKIE_PATH", "/")
AUTH_REFRESH_COOKIE_SAMESITE = env("AUTH_REFRESH_COOKIE_SAMESITE", "Lax")
AUTH_REFRESH_COOKIE_SECURE = env_bool("AUTH_REFRESH_COOKIE_SECURE", not DEBUG)
AUTH_REFRESH_COOKIE_DOMAIN = env("AUTH_REFRESH_COOKIE_DOMAIN") or None
AUTH_REFRESH_COOKIE_DEFAULT_MAX_AGE = int(env("AUTH_REFRESH_COOKIE_DEFAULT_MAX_AGE", 14 * 24 * 60 * 60))
AUTH_REFRESH_COOKIE_REMEMBER_MAX_AGE = int(env("AUTH_REFRESH_COOKIE_REMEMBER_MAX_AGE", 30 * 24 * 60 * 60))
AUTH_REFRESH_COOKIE_REMEMBER_NAME = env("AUTH_REFRESH_COOKIE_REMEMBER_NAME", "corpershub_remember")

VALKEY_URL = env_optional("VALKEY_URL") or env("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": VALKEY_URL,
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [VALKEY_URL]},
    }
}

CELERY_BROKER_URL = VALKEY_URL
CELERY_RESULT_BACKEND = VALKEY_URL
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
OTP_EXPIRY_SECONDS = int(env("OTP_EXPIRY_SECONDS", "600") or "600")
OTP_RESEND_WINDOW_SECONDS = int(env("OTP_RESEND_WINDOW_SECONDS", "60") or "60")
OTP_MAX_ATTEMPTS = int(env("OTP_MAX_ATTEMPTS", "5") or "5")
OTP_EMAIL_ASYNC = env_bool("OTP_EMAIL_ASYNC", True)
SEED_DEFAULT_ACCOUNTS_ENABLED = env_bool("SEED_DEFAULT_ACCOUNTS_ENABLED", False)
DIKRIPT_API_BASE_URL = env("DIKRIPT_API_BASE_URL", "https://api.dikript.com") or "https://api.dikript.com"
DIKRIPT_NIN_API_URL = (
    env("DIKRIPT_NIN_API_URL", "/dikript/verification/api/v1/getnin") or "/dikript/verification/api/v1/getnin"
)
DIKRIPT_CAC_API_URL = (
    env("DIKRIPT_CAC_API_URL", "/dikript/verification/api/v1/getcacbasic") or "/dikript/verification/api/v1/getcacbasic"
)
DIKRIPT_PUBLIC_KEY = env("DIKRIPT_PUBLIC_KEY", "") or ""
DIKRIPT_SECRET_KEY = env("DIKRIPT_SECRET_KEY", "") or ""
DIKRIPT_TIMEOUT_SECONDS = float(env("DIKRIPT_TIMEOUT_SECONDS", "10") or "10")
DIKRIPT_LOOKUP_CACHE_TIMEOUT_SECONDS = int(
    env("DIKRIPT_LOOKUP_CACHE_TIMEOUT_SECONDS", str(60 * 60 * 24)) or str(60 * 60 * 24)
)

HOSTINGER_SMTP_HOST = "smtp.hostinger.com"
HOSTINGER_SMTP_SSL_PORT = 465
HOSTINGER_SMTP_TLS_PORT = 587
HOSTINGER_DEFAULT_FROM_EMAIL = "info@corpershub.ng"

EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", HOSTINGER_SMTP_HOST)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", HOSTINGER_DEFAULT_FROM_EMAIL) or HOSTINGER_DEFAULT_FROM_EMAIL
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "") or ""
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
default_email_port = HOSTINGER_SMTP_SSL_PORT if EMAIL_USE_SSL else HOSTINGER_SMTP_TLS_PORT
EMAIL_PORT = int(env("EMAIL_PORT", str(default_email_port)) or str(default_email_port))
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or HOSTINGER_DEFAULT_FROM_EMAIL)
EMAIL_FROM_EMAIL = env("EMAIL_FROM_EMAIL", "") or EMAIL_HOST_USER or DEFAULT_FROM_EMAIL
SERVER_EMAIL = env("SERVER_EMAIL", EMAIL_FROM_EMAIL)
EMAIL_TIMEOUT = int(env("EMAIL_TIMEOUT", "60") or "60")
WEB_URL = env("WEB_URL", "http://localhost:3000")
COMPANY_VERIFICATION_ADMIN_EMAIL = (
    env("COMPANY_VERIFICATION_ADMIN_EMAIL", "admin@corpershub.ng") or "admin@corpershub.ng"
)

if EMAIL_USE_SSL and EMAIL_USE_TLS:
    raise ImproperlyConfigured("EMAIL_USE_SSL and EMAIL_USE_TLS cannot both be enabled.")

if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and EMAIL_HOST == HOSTINGER_SMTP_HOST:
    valid_hostinger_settings = {
        (HOSTINGER_SMTP_SSL_PORT, True, False),
        (HOSTINGER_SMTP_TLS_PORT, False, True),
    }
    if (EMAIL_PORT, EMAIL_USE_SSL, EMAIL_USE_TLS) not in valid_hostinger_settings:
        raise ImproperlyConfigured(
            "Hostinger SMTP must use port 465 with EMAIL_USE_SSL=True and EMAIL_USE_TLS=False, "
            "or port 587 with EMAIL_USE_SSL=False and EMAIL_USE_TLS=True."
        )

AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "")
AWS_S3_ENDPOINT_URL = env_optional("AWS_S3_ENDPOINT_URL")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", "")
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", "")
AWS_S3_ADDRESSING_STYLE = env("AWS_S3_ADDRESSING_STYLE", "auto")
AWS_S3_URL_PROTOCOL = env("AWS_S3_URL_PROTOCOL", "https:")
AWS_QUERYSTRING_AUTH = False
AWS_DEFAULT_ACL = None


def build_storages(bucket_name: str) -> dict[str, dict[str, str]]:
    storages = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    if bucket_name:
        storages["default"] = {
            "BACKEND": "apps.common.storage.PublicMediaStorage",
        }
    return storages


STORAGES = build_storages(AWS_STORAGE_BUCKET_NAME)


def build_field_encryption_key() -> str:
    configured = env("FIELD_ENCRYPTION_KEY")
    if configured:
        return configured
    digest = hashlib.sha256(SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8")


FIELD_ENCRYPTION_KEY = build_field_encryption_key()

FLUTTERWAVE_CLIENT_ID = env("FLUTTERWAVE_CLIENT_ID", "") or ""
FLUTTERWAVE_CLIENT_SECRET = env("FLUTTERWAVE_CLIENT_SECRET", "") or ""
FLUTTERWAVE_PUBLIC_KEY = env("FLUTTERWAVE_PUBLIC_KEY", "") or ""
FLUTTERWAVE_SECRET_KEY = env("FLUTTERWAVE_SECRET_KEY", "") or ""
FLUTTERWAVE_ENCRYPTION_KEY = env("FLUTTERWAVE_ENCRYPTION_KEY", "") or ""
FLUTTERWAVE_WEBHOOK_SECRET_HASH = env("FLUTTERWAVE_WEBHOOK_SECRET_HASH", "") or ""
FLUTTERWAVE_API_BASE_URL = env("FLUTTERWAVE_API_BASE_URL") or "https://f4bexperience.flutterwave.com"
FLUTTERWAVE_V3_API_BASE_URL = env("FLUTTERWAVE_V3_API_BASE_URL", "https://api.flutterwave.com/v3") or ""
FLUTTERWAVE_TOKEN_URL = (
    env("FLUTTERWAVE_TOKEN_URL") or "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"
)
FLUTTERWAVE_SETTLEMENT_BANK_NAME = env("FLUTTERWAVE_SETTLEMENT_BANK_NAME", "Providus Bank") or ""
FLUTTERWAVE_SETTLEMENT_ACCOUNT_NUMBER = env("FLUTTERWAVE_SETTLEMENT_ACCOUNT_NUMBER", "1309659188") or ""

FREE_EMAIL_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
}

# Temporary exception for company signup testing.
COMPANY_EMAIL_TEST_ALLOWLIST = {
    "gmail.com",
    "hotmail.com",
    "outlook.com",
}
