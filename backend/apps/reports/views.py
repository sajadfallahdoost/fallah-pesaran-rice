import csv
import datetime as dt

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.response import TemplateResponse

from apps.core.dates import parse_jalali_date, tehran_today, to_jalali_str
from apps.core.money import format_toman
from apps.reports import services

PRESETS = {"today": 0, "7d": 6, "30d": 29, "90d": 89}


def _require_permission(request):
    if not request.user.has_perm("orders.view_financial_reports"):
        raise PermissionDenied


def _include_test(request) -> bool:
    return request.GET.get("include_test") == "1"


def _date_range(request) -> tuple[dt.date, dt.date, str, str]:
    today = tehran_today()
    preset = request.GET.get("preset", "")
    start = parse_jalali_date(request.GET.get("from", ""))
    end = parse_jalali_date(request.GET.get("to", ""))
    if preset in PRESETS or not (start and end):
        days = PRESETS.get(preset, 29)
        start, end = today - dt.timedelta(days=days), today
    if start > end:
        start, end = end, start
    return start, end, to_jalali_str(start, with_time=False), to_jalali_str(end, with_time=False)


def sales_report(request):
    _require_permission(request)
    start, end, start_label, end_label = _date_range(request)
    include_test = _include_test(request)
    summary = services.summary(start, end, include_test)
    monthly = (end - start).days > 62
    trend = [
        {
            **row,
            "label": to_jalali_str(row["period"], with_time=False),
            "paid_display": format_toman(row["paid"] or 0),
            "sales_display": format_toman(row["sales"] or 0),
        }
        for row in services.trend(start, end, monthly=monthly, include_test=include_test)
    ]
    max_paid = max((row["paid"] or 0 for row in trend), default=0) or 1
    for row in trend:
        row["bar"] = round(100 * (row["paid"] or 0) / max_paid)

    attempts = services.payment_attempts(start, end, include_test)
    context = {
        **admin.site.each_context(request),
        "title": "گزارش فروش و پرداخت",
        "start_label": start_label,
        "end_label": end_label,
        "query": request.GET.urlencode(),
        "include_test": include_test,
        "summary": summary,
        "money": {
            key: format_toman(getattr(summary, key))
            for key in (
                "gross_merchandise",
                "discounts",
                "tax",
                "shipping",
                "customer_payments",
                "refunds",
                "net_sales",
                "average_order_value",
            )
        },
        "trend": trend,
        "monthly": monthly,
        "top_products": [
            {**p, "revenue_display": format_toman(p["revenue"])}
            for p in services.top_products(start, end, include_test=include_test)
        ],
        "categories": [
            {**c, "revenue_display": format_toman(c["revenue"])}
            for c in services.category_sales(start, end, include_test)
        ],
        "attempts_by_status": [
            {
                "label": label,
                "count": attempts["by_status"].get(code, {}).get("count", 0),
                "amount": format_toman(attempts["by_status"].get(code, {}).get("amount") or 0),
            }
            for code, label in services.PaymentAttempt.Status.choices
        ],
        "payment_exceptions": attempts["exceptions"],
        "review_orders": services.review_orders(),
        "low_stock": services.stock_overview()["low_stock"],
    }
    return TemplateResponse(request, "admin/reports/sales_report.html", context)


def export_csv(request, kind: str):
    _require_permission(request)
    start, end, start_label, end_label = _date_range(request)
    include_test = _include_test(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{kind}-{start.isoformat()}-{end.isoformat()}.csv"'
    response["Cache-Control"] = "private, no-store"
    response.write("\ufeff")  # BOM so spreadsheet apps detect UTF-8 Persian text
    writer = csv.writer(response)
    safe = services.csv_safe

    if kind == "orders":
        writer.writerow(
            [
                "شماره سفارش",
                "تاریخ پرداخت",
                "وضعیت پرداخت",
                "وضعیت ارسال",
                "جمع کالا (ریال)",
                "تخفیف (ریال)",
                "مالیات (ریال)",
                "ارسال (ریال)",
                "مبلغ پرداختی (ریال)",
                "روش ارسال",
                "استان",
                "شهر",
            ]
        )
        for o in services.paid_orders(start, end, include_test).order_by("paid_at"):
            writer.writerow(
                [
                    safe(v)
                    for v in (
                        o.number,
                        to_jalali_str(o.paid_at),
                        o.get_payment_status_display(),
                        o.get_fulfillment_status_display(),
                        o.merchandise_total,
                        o.discount_total,
                        o.tax_total,
                        o.shipping_total,
                        o.grand_total,
                        o.shipping_method_name,
                        o.province_name,
                        o.city,
                    )
                ]
            )
    elif kind == "order-lines":
        writer.writerow(
            [
                "شماره سفارش",
                "تاریخ پرداخت",
                "محصول",
                "بسته",
                "SKU",
                "تعداد",
                "قیمت واحد (ریال)",
                "تخفیف ردیف (ریال)",
                "جمع ردیف (ریال)",
            ]
        )
        items = (
            services.paid_order_items(start, end, include_test).select_related("order").order_by("order__paid_at", "id")
        )
        for i in items:
            writer.writerow(
                [
                    safe(v)
                    for v in (
                        i.order.number,
                        to_jalali_str(i.order.paid_at),
                        i.product_name,
                        i.variant_title,
                        i.sku,
                        i.quantity,
                        i.unit_price,
                        i.line_discount,
                        i.line_total,
                    )
                ]
            )
    elif kind == "summary":
        s = services.summary(start, end, include_test)
        writer.writerow(
            [
                "از",
                "تا",
                "سفارش پرداخت‌شده",
                "فروش ناخالص کالا",
                "تخفیف",
                "مالیات",
                "ارسال دریافتی",
                "پرداخت مشتریان",
                "بازپرداخت",
                "فروش خالص",
                "میانگین سفارش",
            ]
        )
        writer.writerow(
            [
                safe(v)
                for v in (
                    start_label,
                    end_label,
                    s.paid_orders,
                    s.gross_merchandise,
                    s.discounts,
                    s.tax,
                    s.shipping,
                    s.customer_payments,
                    s.refunds,
                    s.net_sales,
                    s.average_order_value,
                )
            ]
        )
    else:
        return HttpResponse(status=404)
    return response
