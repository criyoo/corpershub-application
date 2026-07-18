from .base import *  # noqa: F403,F401

DEBUG = True
SEED_DEMO_ACCOUNTS = True

LOCAL_USE_SMTP_EMAIL = env_bool("LOCAL_USE_SMTP_EMAIL", False)  # noqa: F405
if not LOCAL_USE_SMTP_EMAIL:
    EMAIL_BACKEND = env(  # noqa: F405
        "LOCAL_EMAIL_BACKEND",
        "django.core.mail.backends.console.EmailBackend",
    )

OTP_EMAIL_FALLBACK_ENABLED = env_bool(  # noqa: F405
    "OTP_EMAIL_FALLBACK_ENABLED",
    not LOCAL_USE_SMTP_EMAIL,
)
OTP_EMAIL_FALLBACK_BACKEND = env(  # noqa: F405
    "OTP_EMAIL_FALLBACK_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

FLUTTERWAVE_API_VERSION = env("FLUTTERWAVE_API_VERSION", "v3")  # noqa: F405
FLUTTERWAVE_PUBLIC_KEY = (
    env(  # noqa: F405
        "FLUTTERWAVE_PUBLIC_KEY",
        "FLWPUBK_TEST-e6a0023b4fa777353ecd0ee155335307-X",
    )
    or "FLWPUBK_TEST-e6a0023b4fa777353ecd0ee155335307-X"
)
FLUTTERWAVE_SECRET_KEY = (
    env(  # noqa: F405
        "FLUTTERWAVE_SECRET_KEY",
        "FLWSECK_TEST-40e097e8dbdf09458368ccaa8472189f-X",
    )
    or "FLWSECK_TEST-40e097e8dbdf09458368ccaa8472189f-X"
)
FLUTTERWAVE_ENCRYPTION_KEY = (
    env(  # noqa: F405
        "FLUTTERWAVE_ENCRYPTION_KEY",
        "FLWSECK_TEST820964fec1fa",
    )
    or "FLWSECK_TEST820964fec1fa"
)
FLUTTERWAVE_API_BASE_URL = (
    env(  # noqa: F405
        "FLUTTERWAVE_API_BASE_URL",
        "https://developersandbox-api.flutterwave.com",
    )
    or "https://developersandbox-api.flutterwave.com"
)
FLUTTERWAVE_V3_API_BASE_URL = (
    env(  # noqa: F405
        "FLUTTERWAVE_V3_API_BASE_URL",
        "https://developersandbox-api.flutterwave.com/v3",
    )
    or "https://developersandbox-api.flutterwave.com/v3"
)
FLUTTERWAVE_TOKEN_URL = (
    env(  # noqa: F405
        "FLUTTERWAVE_TOKEN_URL",
        "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token",
    )
    or "https://idp.flutterwave.com/realms/flutterwave/protocol/openid-connect/token"
)
