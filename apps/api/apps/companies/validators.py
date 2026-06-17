TAX_IDENTIFICATION_NUMBER_VALIDATION_MESSAGE = "Enter a valid tax identification number with 10 to 13 digits."


def normalize_tax_identification_number(value):
    return str(value or "").strip()


def is_valid_tax_identification_number(value):
    normalized = normalize_tax_identification_number(value)
    return normalized.isdigit() and 10 <= len(normalized) <= 13
