"""Persian RTL order receipt rendered to PDF (WeasyPrint shapes Persian text with HarfBuzz)."""

from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

from apps.core.dates import to_jalali_str
from apps.core.models import StoreSettings
from apps.core.money import fa_digits, format_toman
from apps.orders.models import Order

FONT_DIR = Path(settings.BASE_DIR) / "static" / "fonts"


def invoice_context(order: Order) -> dict:
    store = StoreSettings.load()
    payment = order.payment_attempts.filter(applied_to_order=True).first()
    unit_labels = {"kg": "کیلوگرم", "g": "گرم", "l": "لیتر", "ml": "میلی‌لیتر", "piece": "عدد"}
    items = [
        {
            "name": item.product_name,
            "variant": item.variant_title,
            "sku": item.sku,
            "package": f"{fa_digits(item.package_amount.normalize())} {unit_labels.get(item.package_unit, '')}",
            "quantity": fa_digits(item.quantity),
            "list_unit_price": format_toman(item.list_unit_price),
            "unit_price": format_toman(item.unit_price),
            "discount": format_toman(item.line_discount) if item.line_discount else "—",
            "line_total": format_toman(item.line_total),
        }
        for item in order.items.all()
    ]
    return {
        "store": store,
        "order": order,
        "invoice": order.invoice,
        "issued_at": to_jalali_str(order.invoice.issued_at),
        "paid_at": to_jalali_str(order.paid_at),
        "created_at": to_jalali_str(order.created_at),
        "items": items,
        "merchandise_total": format_toman(order.merchandise_total),
        "discount_total": format_toman(order.discount_total),
        "tax_total": format_toman(order.tax_total),
        "shipping_total": format_toman(order.shipping_total),
        "grand_total": format_toman(order.grand_total),
        "payment_reference": payment.reference_number if payment else "",
        "payment_provider": payment.provider if payment else "",
        "font_dir": FONT_DIR.as_uri(),
        "logo_uri": (Path(settings.BASE_DIR) / "static" / "brand" / "fallah-emblem.png").as_uri(),
    }


def render_invoice_html(order: Order) -> str:
    return render_to_string("orders/invoice.html", invoice_context(order))


def render_invoice_pdf(order: Order) -> bytes:
    from weasyprint import HTML

    return HTML(string=render_invoice_html(order), base_url=str(settings.BASE_DIR)).write_pdf()
