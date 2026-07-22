from __future__ import annotations

import re

from rest_framework import serializers

NIGERIAN_MOBILE_PREFIXES = frozenset(
    {
        "0701",
        "0702",
        "0703",
        "0704",
        "0705",
        "0706",
        "0707",
        "0708",
        "0709",
        "07025",
        "07026",
        "07027",
        "07028",
        "07029",
        "0802",
        "0803",
        "0804",
        "0805",
        "0806",
        "0807",
        "0808",
        "0809",
        "0810",
        "0811",
        "0812",
        "0813",
        "0814",
        "0815",
        "0816",
        "0817",
        "0818",
        "0819",
        "0901",
        "0902",
        "0903",
        "0904",
        "0905",
        "0906",
        "0907",
        "0908",
        "0909",
        "0911",
        "0912",
        "0913",
        "0915",
        "0916",
        "0917",
    }
)
NYSC_CALLUP_NUMBER_RE = re.compile(r"^NYSC/[A-Z]{3}/\d{4}/\d{4,6}$")
NYSC_STATE_CODE_RE = re.compile(r"^NYSC/[A-Z]{2}/\d{2}[A-C]/\d{5,6}$")
UNIVERSITY_MATRICULATION_NUMBER_RE = re.compile(r"^[A-Z0-9/]{8,16}$")


def normalize_mobile_number(value: str | None) -> str:
    return re.sub(r"[\s-]+", "", (value or "").strip())


def normalize_nigerian_mobile_number_to_international(value: str | None) -> str:
    mobile_number = normalize_mobile_number(value)
    if not mobile_number:
        return ""
    if mobile_number.startswith("+234"):
        return f"+234{mobile_number[4:]}"
    if mobile_number.startswith("234"):
        return f"+{mobile_number}"
    if mobile_number.startswith("0"):
        return f"+234{mobile_number[1:]}"
    return mobile_number


def validate_nigerian_mobile_number(
    value: str | None,
    *,
    required: bool = True,
    field_label: str = "Mobile number",
    require_international_format: bool = False,
) -> str:
    mobile_number = normalize_mobile_number(value)
    if not mobile_number:
        if required:
            raise serializers.ValidationError(f"{field_label} is required.")
        return ""

    if mobile_number.startswith("+"):
        if not re.fullmatch(r"\+\d+", mobile_number):
            raise serializers.ValidationError(
                f"Enter a valid {field_label.lower()} using only digits and an optional leading +."
            )
        if not mobile_number.startswith("+234"):
            raise serializers.ValidationError(f"Enter a valid Nigerian {field_label.lower()} starting with +234.")
        if len(mobile_number) != 14:
            raise serializers.ValidationError("Numbers starting with +234 must contain 13 digits excluding the +.")
        local_number = f"0{mobile_number[4:]}"
    else:
        if require_international_format:
            raise serializers.ValidationError(f"Enter a valid Nigerian {field_label.lower()} starting with +234.")
        if not mobile_number.isdigit():
            raise serializers.ValidationError(f"Enter a valid {field_label.lower()} using digits only.")
        if not mobile_number.startswith("0"):
            raise serializers.ValidationError(f"Enter a valid Nigerian {field_label.lower()} starting with 0 or +234.")
        if len(mobile_number) != 11:
            raise serializers.ValidationError("Numbers starting with 0 must contain 11 digits.")
        local_number = mobile_number

    if len(local_number) != 11:
        raise serializers.ValidationError("Enter a valid Nigerian mobile number.")

    if not any(local_number.startswith(prefix) for prefix in NIGERIAN_MOBILE_PREFIXES):
        raise serializers.ValidationError("Enter a valid Nigerian mobile number with a supported network prefix.")

    return mobile_number


def normalize_nin_number(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip())


def validate_nin_number(value: str | None) -> str:
    nin_number = normalize_nin_number(value)
    if not nin_number:
        raise serializers.ValidationError("NIN Number is required.")
    if not re.fullmatch(r"\d{11}", nin_number):
        raise serializers.ValidationError("NIN Number must be exactly 11 digits.")
    return nin_number


def normalize_nysc_callup_number(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


def validate_nysc_callup_number(value: str | None) -> str:
    callup_number = normalize_nysc_callup_number(value)
    if not callup_number:
        raise serializers.ValidationError("NYSC Call-up Number is required.")
    if not NYSC_CALLUP_NUMBER_RE.fullmatch(callup_number):
        raise serializers.ValidationError("NYSC Call-up Number must match the format NYSC/ABC/2024/1234.")
    return callup_number


def normalize_nysc_state_code(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


def validate_nysc_state_code(value: str | None) -> str:
    state_code = normalize_nysc_state_code(value)
    if not state_code:
        raise serializers.ValidationError("NYSC State Code is required.")
    if not NYSC_STATE_CODE_RE.fullmatch(state_code):
        raise serializers.ValidationError("NYSC State Code must match the format NYSC/LG/26B/72673.")

    return state_code


def normalize_university_matriculation_number(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip().upper())


def validate_university_matriculation_number(value: str | None) -> str:
    matriculation_number = normalize_university_matriculation_number(value)
    if not matriculation_number:
        raise serializers.ValidationError("University Matriculation Number is required.")
    if not UNIVERSITY_MATRICULATION_NUMBER_RE.fullmatch(matriculation_number):
        raise serializers.ValidationError(
            'University Matriculation Number must be 8 to 16 characters using only letters, numbers, and "/".'
        )
    return matriculation_number
