from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def get_fernet() -> Fernet:
    return Fernet(settings.FIELD_ENCRYPTION_KEY.encode("utf-8"))


class EncryptedCharField(models.TextField):
    description = "Encrypted text field"

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return get_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise ValidationError("Unable to decrypt field value.") from exc

    def to_python(self, value):
        return value

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        return get_fernet().encrypt(str(value).encode("utf-8")).decode("utf-8")
