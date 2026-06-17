from __future__ import annotations

import secrets
import string
from datetime import date


def generate_alphanumeric_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def calculate_age(date_of_birth: date | None) -> int | None:
    if not date_of_birth:
        return None
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


def mask_identifier(value: str | None, prefix: int = 2, suffix: int = 2) -> str:
    if not value:
        return ""
    if len(value) <= prefix + suffix:
        return "*" * len(value)
    middle = "*" * (len(value) - prefix - suffix)
    return f"{value[:prefix]}{middle}{value[-suffix:]}"
