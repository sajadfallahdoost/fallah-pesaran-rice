"""Money rules.

Canonical storage: integer Iranian rial (IRR) in BigIntegerField columns. Never floats.
Customer-facing presentation: toman (1 toman = 10 rial). Prices are required to be
whole tomans (multiples of 10 rial) so presentation never rounds.
"""

from django.core.exceptions import ValidationError

CURRENCY = "IRR"
RIAL_PER_TOMAN = 10

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def validate_whole_toman(value: int) -> None:
    if value is None:
        return
    if value < 0:
        raise ValidationError("مبلغ نمی‌تواند منفی باشد.")
    if value % RIAL_PER_TOMAN:
        raise ValidationError("مبلغ باید مضرب ۱۰ ریال (تومان کامل) باشد.")


def rial_to_toman(amount_rial: int) -> int:
    return amount_rial // RIAL_PER_TOMAN


def format_toman(amount_rial: int) -> str:
    """'۱٬۲۵۰٬۰۰۰ تومان' for display in admin, invoices, and SMS."""
    toman = rial_to_toman(int(amount_rial or 0))
    return f"{toman:,}".replace(",", "٬").translate(_FA_DIGITS) + " تومان"


def format_rial(amount_rial: int) -> str:
    return f"{int(amount_rial or 0):,}".replace(",", "٬").translate(_FA_DIGITS) + " ریال"


def fa_digits(value) -> str:
    return str(value).translate(_FA_DIGITS)
