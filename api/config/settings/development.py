from .base import *  # noqa: F403,F401

DEBUG = True
SEED_DEMO_ACCOUNTS = True

# AWS dev must use the configured SMTP backend, not the local console backend.
OTP_EMAIL_FALLBACK_ENABLED = env_bool("OTP_EMAIL_FALLBACK_ENABLED", False)  # noqa: F405
