"""Persian text helpers: digit normalization, phone validation, Arabic letter folding."""

import re

_DIGIT_MAP = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_LETTER_MAP = str.maketrans({"ي": "ی", "ك": "ک", "ى": "ی", "ة": "ه"})
_IRAN_MOBILE = re.compile(r"^09\d{9}$")


def normalize_digits(value: str) -> str:
    """Convert Persian and Arabic-Indic digits to ASCII digits."""
    return (value or "").translate(_DIGIT_MAP)


def normalize_text(value: str) -> str:
    """Fold Arabic letter variants to Persian ones and collapse whitespace (search, cities)."""
    value = normalize_digits(value or "").translate(_LETTER_MAP)
    return re.sub(r"\s+", " ", value).strip()


def normalize_phone(value: str) -> str | None:
    """Return an Iranian mobile number as 09xxxxxxxxx, or None if invalid."""
    digits = re.sub(r"[\s\-()]", "", normalize_digits(value or ""))
    if digits.startswith("+98"):
        digits = "0" + digits[3:]
    elif digits.startswith("0098"):
        digits = "0" + digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    return digits if _IRAN_MOBILE.match(digits) else None


def normalize_postal_code(value: str) -> str:
    return re.sub(r"\D", "", normalize_digits(value or ""))
