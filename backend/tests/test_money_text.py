import datetime as dt

import pytest
from django.core.exceptions import ValidationError

from apps.core.dates import parse_jalali_date, tehran_day_bounds, to_jalali_str
from apps.core.money import fa_digits, format_toman, rial_to_toman, validate_whole_toman
from apps.core.text import normalize_digits, normalize_phone, normalize_postal_code, normalize_text
from apps.reports.services import csv_safe

pytestmark = pytest.mark.django_db


def test_rial_to_toman_and_format():
    assert rial_to_toman(17_500_000) == 1_750_000
    assert format_toman(17_500_000) == "۱٬۷۵۰٬۰۰۰ تومان"
    assert fa_digits("123") == "۱۲۳"


def test_whole_toman_validator():
    validate_whole_toman(10)
    with pytest.raises(ValidationError):
        validate_whole_toman(15)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("۰۹۱۲۲۱۲۲۱۸۷", "09122122187"),
        ("+98 912 212 2187", "09122122187"),
        ("00989122122187", "09122122187"),
        ("9122122187", "09122122187"),
        ("٠٩١٢٢١٢٢١٨٧", "09122122187"),
        ("0212345678", None),
        ("abc", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


def test_normalize_text_and_digits():
    assert normalize_text("علي كريمي") == "علی کریمی"
    assert normalize_digits("۱۲۳٤") == "1234"
    assert normalize_postal_code("۱۲۳۴۵-۶۷۸۹۰") == "1234567890"


def test_jalali_round_trip_and_tehran_bounds():
    day = parse_jalali_date("۱۴۰۵/۰۸/۲۸")
    assert day == dt.date(2026, 11, 19)
    assert to_jalali_str(day, with_time=False) == "۱۴۰۵/۰۸/۲۸"
    lower, upper = tehran_day_bounds(day, day)
    # Tehran is UTC+03:30 (no DST since 2022): the business day starts 20:30 UTC the previous day.
    assert lower.astimezone(dt.UTC) == dt.datetime(2026, 11, 18, 20, 30, tzinfo=dt.UTC)
    assert upper - lower == dt.timedelta(days=1)


@pytest.mark.parametrize("value", ["=SUM(A1)", "+1", "-2", "@cmd", "\tx"])
def test_csv_formula_injection_neutralized(value):
    assert csv_safe(value).startswith("'")
    assert csv_safe(-50) == "-50"  # numbers stay numeric
