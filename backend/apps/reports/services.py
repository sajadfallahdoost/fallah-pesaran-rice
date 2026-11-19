"""Sales and payment reporting from persisted, verified data only.

Definitions (documented in docs/ARCHITECTURE.md#reports):
- Paid order: payment_status != unpaid, is_test = False (unless the owner opts in to test data), counted on paid_at (Asia/Tehran days).
- Gross merchandise sales = Σ merchandise_total (list prices × quantity) of paid orders.
- Discounts = Σ discount_total. Tax = Σ tax_total. Shipping collected = Σ shipping_total.
- Customer payments = Σ grand_total of paid orders (what gateways verified).
- Refunds = Σ amount of refunds with status completed, counted on completed_at.
- Net sales = gross merchandise − discounts − refunds (shipping and tax shown separately).
No cost data exists, so no profit is reported. Gateway settlement to the bank account is not tracked.
"""

import datetime as dt
from dataclasses import dataclass

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth

from apps.catalog.models import ProductVariant
from apps.core.dates import TEHRAN, tehran_day_bounds
from apps.orders.models import Order, OrderItem, Refund
from apps.payments.models import PaymentAttempt


@dataclass
class SalesSummary:
    paid_orders: int
    gross_merchandise: int
    discounts: int
    tax: int
    shipping: int
    customer_payments: int
    refunds: int
    net_sales: int
    average_order_value: int


def paid_orders(start: dt.date, end: dt.date, include_test: bool = False):
    lower, upper = tehran_day_bounds(start, end)
    qs = Order.objects.filter(paid_at__gte=lower, paid_at__lt=upper).exclude(payment_status=Order.PaymentStatus.UNPAID)
    return qs if include_test else qs.filter(is_test=False)


def paid_order_items(start: dt.date, end: dt.date, include_test: bool = False):
    return OrderItem.objects.filter(order__in=paid_orders(start, end, include_test))


def completed_refunds(start: dt.date, end: dt.date, include_test: bool = False):
    lower, upper = tehran_day_bounds(start, end)
    qs = Refund.objects.filter(status=Refund.Status.COMPLETED, completed_at__gte=lower, completed_at__lt=upper)
    return qs if include_test else qs.filter(order__is_test=False)


def summary(start: dt.date, end: dt.date, include_test: bool = False) -> SalesSummary:
    agg = paid_orders(start, end, include_test).aggregate(
        count=Count("id"),
        gross=Sum("merchandise_total"),
        discounts=Sum("discount_total"),
        tax=Sum("tax_total"),
        shipping=Sum("shipping_total"),
        payments=Sum("grand_total"),
    )
    refunds = completed_refunds(start, end, include_test).aggregate(total=Sum("amount"))["total"] or 0
    count = agg["count"] or 0
    gross = agg["gross"] or 0
    discounts = agg["discounts"] or 0
    payments = agg["payments"] or 0
    return SalesSummary(
        paid_orders=count,
        gross_merchandise=gross,
        discounts=discounts,
        tax=agg["tax"] or 0,
        shipping=agg["shipping"] or 0,
        customer_payments=payments,
        refunds=refunds,
        net_sales=gross - discounts - refunds,
        average_order_value=payments // count if count else 0,
    )


def trend(start: dt.date, end: dt.date, monthly: bool = False, include_test: bool = False) -> list[dict]:
    trunc = TruncMonth("paid_at", tzinfo=TEHRAN) if monthly else TruncDate("paid_at", tzinfo=TEHRAN)
    return list(
        paid_orders(start, end, include_test)
        .annotate(period=trunc)
        .values("period")
        .annotate(orders=Count("id"), sales=Sum(F("merchandise_total") - F("discount_total")), paid=Sum("grand_total"))
        .order_by("period")
    )


def top_products(start: dt.date, end: dt.date, limit: int = 10, include_test: bool = False) -> list[dict]:
    return list(
        paid_order_items(start, end, include_test)
        .values("product_name", "variant_title", "sku")
        .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-revenue")[:limit]
    )


def category_sales(start: dt.date, end: dt.date, include_test: bool = False) -> list[dict]:
    return list(
        paid_order_items(start, end, include_test)
        .values(category=F("variant__product__category__name"))
        .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-revenue")
    )


def payment_attempts(start: dt.date, end: dt.date, include_test: bool = False) -> dict:
    lower, upper = tehran_day_bounds(start, end)
    qs = PaymentAttempt.objects.filter(created_at__gte=lower, created_at__lt=upper)
    if not include_test:
        qs = qs.filter(is_test=False)
    base = PaymentAttempt.objects.all() if include_test else PaymentAttempt.objects.filter(is_test=False)
    by_status = {row["status"]: row for row in qs.values("status").annotate(count=Count("id"), amount=Sum("amount"))}
    exceptions = list(
        base.filter(
            Q(status__in=[PaymentAttempt.Status.UNKNOWN, PaymentAttempt.Status.MISMATCH])
            | Q(status=PaymentAttempt.Status.SUCCEEDED, applied_to_order=False)
        )
        .select_related("order")
        .order_by("-created_at")[:50]
    )
    return {"by_status": by_status, "exceptions": exceptions}


def stock_overview() -> dict:
    variants = ProductVariant.objects.filter(is_active=True).select_related("product")
    low = [v for v in variants if v.stock <= v.low_stock_threshold]
    return {"low_stock": sorted(low, key=lambda v: v.stock)}


def review_orders():
    return Order.objects.filter(needs_review=True).order_by("-updated_at")[:50]


def csv_safe(value) -> str:
    """Neutralize spreadsheet formula injection in exported cells."""
    if isinstance(value, int):
        return str(value)
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text
