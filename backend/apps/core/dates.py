"""Persian (Jalali) calendar presentation and Asia/Tehran business-day boundaries."""

import datetime as dt
from zoneinfo import ZoneInfo

import jdatetime
from django.utils import timezone

from apps.core.money import fa_digits

TEHRAN = ZoneInfo("Asia/Tehran")


def to_jalali_str(value: dt.datetime | dt.date | None, with_time: bool = True) -> str:
    if value is None:
        return "—"
    if isinstance(value, dt.datetime):
        local = timezone.localtime(value, TEHRAN)
        jd = jdatetime.datetime.fromgregorian(datetime=local)
        text = jd.strftime("%Y/%m/%d %H:%M") if with_time else jd.strftime("%Y/%m/%d")
    else:
        text = jdatetime.date.fromgregorian(date=value).strftime("%Y/%m/%d")
    return fa_digits(text)


def parse_jalali_date(text: str) -> dt.date | None:
    """Parse 'YYYY/MM/DD' Jalali (Persian or Latin digits) into a Gregorian date."""
    from apps.core.text import normalize_digits

    text = normalize_digits((text or "").strip()).replace("-", "/")
    if not text:
        return None
    try:
        year, month, day = (int(p) for p in text.split("/"))
        return jdatetime.date(year, month, day).togregorian()
    except (ValueError, TypeError):
        return None


def tehran_day_bounds(start: dt.date, end: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """Half-open [start 00:00, end+1 00:00) range in Asia/Tehran, as aware datetimes."""
    lower = dt.datetime.combine(start, dt.time.min, tzinfo=TEHRAN)
    upper = dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=TEHRAN)
    return lower, upper


def tehran_today() -> dt.date:
    return timezone.localtime(timezone.now(), TEHRAN).date()
