"""Admin form helpers: money is entered in toman and stored in rial."""

import re

from django import forms
from django.utils.html import format_html

from apps.core.money import RIAL_PER_TOMAN, format_toman
from apps.core.text import normalize_digits


class TomanField(forms.IntegerField):
    """Shows/accepts toman (Persian digits and separators allowed); cleans to integer rial."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "widget", forms.TextInput(attrs={"inputmode": "numeric", "dir": "ltr", "class": "vTextField fs-money"})
        )
        kwargs.pop("max_value", None)
        kwargs.pop("min_value", None)
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, int):
            return value // RIAL_PER_TOMAN
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        cleaned = re.sub(r"[,\s٬،_]", "", normalize_digits(str(value)))
        if not cleaned.isdigit():
            raise forms.ValidationError("مبلغ را فقط با عدد و به تومان وارد کنید.")
        return int(cleaned) * RIAL_PER_TOMAN

    def has_changed(self, initial, data):
        try:
            return self.to_python(data) != initial
        except forms.ValidationError:
            return True


class TomanAdminMixin:
    """Render the listed BigInteger rial fields as toman inputs."""

    toman_fields: tuple[str, ...] = ()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in self.toman_fields:
            label = str(db_field.verbose_name).replace("(ریال)", "(تومان)")
            return TomanField(
                label=label,
                required=not db_field.blank,
                help_text="به تومان وارد کنید؛ ذخیره به ریال انجام می‌شود.",
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)


def toman(value) -> str:
    return format_toman(value or 0)


def image_preview(field, size: int = 64):
    if not field:
        return "—"
    return format_html(
        '<img src="{}" alt="" style="inline-size:{}px;block-size:{}px;object-fit:cover;border-radius:6px">',
        field.url,
        size,
        size,
    )
