"""Checkout: turns the server-side cart into a pending order with reserved stock."""

import hashlib
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.api import ApiError
from apps.core.models import StoreSettings, audit
from apps.core.text import normalize_phone, normalize_postal_code, normalize_text
from apps.orders.models import Cart, Order, OrderEvent, OrderItem
from apps.orders.services.inventory import lock_variants
from apps.orders.services.pricing import PricedCart, price_lines, tax_for
from apps.shipping.models import Province, ShippingMethod
from apps.shipping.services import ShippingOption, quote_shipping


@dataclass
class CheckoutInput:
    full_name: str
    phone: str
    email: str
    province_id: int | None
    city: str
    address_line: str
    postal_code: str
    shipping_method_id: int
    customer_note: str = ""


@dataclass
class Totals:
    merchandise_total: int
    discount_total: int
    tax_total: int
    shipping_total: int
    grand_total: int


def compute_totals(priced: PricedCart, option: ShippingOption | None, store: StoreSettings) -> Totals:
    subtotal = priced.subtotal
    tax = tax_for(subtotal, store)
    shipping = option.cost if option and option.available else 0
    return Totals(priced.merchandise_total, priced.discount_total, tax, shipping, subtotal + tax + shipping)


def _validate_customer(data: CheckoutInput, method: ShippingMethod) -> tuple[dict, Province | None]:
    errors: dict[str, str] = {}
    cleaned: dict = {}
    full_name = normalize_text(data.full_name)
    if len(full_name) < 3:
        errors["full_name"] = "نام و نام خانوادگی گیرنده را کامل بنویسید."
    phone = normalize_phone(data.phone)
    if not phone:
        errors["phone"] = "شمارهٔ موبایل معتبر نیست. نمونه: ۰۹۱۲۱۲۳۴۵۶۷"
    province = None
    if method.requires_address:
        province = Province.objects.filter(pk=data.province_id).first() if data.province_id else None
        if province is None:
            errors["province_id"] = "استان را انتخاب کنید."
        if len(normalize_text(data.city)) < 2:
            errors["city"] = "شهر را بنویسید."
        if len(normalize_text(data.address_line)) < 10:
            errors["address_line"] = "نشانی را کامل‌تر بنویسید (خیابان، کوچه، پلاک، واحد)."
        postal = normalize_postal_code(data.postal_code)
        if postal and len(postal) != 10:
            errors["postal_code"] = "کد پستی باید ۱۰ رقم باشد."
        cleaned["postal_code"] = postal
    if errors:
        raise ApiError("لطفاً اطلاعات ارسال را بررسی کنید.", code="invalid_address", fields=errors)
    cleaned.update(
        full_name=full_name,
        phone=phone,
        email=(data.email or "").strip()[:254],
        city=normalize_text(data.city) if method.requires_address else "",
        address_line=normalize_text(data.address_line) if method.requires_address else "",
        customer_note=(data.customer_note or "").strip()[:500],
    )
    return cleaned, province


def place_order(
    *, cart: Cart | None, user, data: CheckoutInput, idempotency_key: str, expected_total: int | None
) -> Order:
    # Scoped to the cart so a replayed key from another session cannot fetch someone else's order.
    if idempotency_key:
        scope = str(cart.token) if cart is not None else ""
        idempotency_key = hashlib.sha256(f"{scope}:{idempotency_key}".encode()).hexdigest()
        existing = Order.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing

    store = StoreSettings.load()
    if not store.sales_enabled:
        raise ApiError("ثبت سفارش موقتاً غیرفعال است.", code="sales_disabled", status_code=503)
    if cart is None or not cart.items.exists():
        raise ApiError("سبد خرید شما خالی است.", code="empty_cart")

    method = ShippingMethod.objects.filter(pk=data.shipping_method_id, is_active=True).first()
    if method is None:
        raise ApiError("روش ارسال انتخاب‌شده در دسترس نیست.", code="shipping_unavailable")
    cleaned, province = _validate_customer(data, method)

    try:
        with transaction.atomic():
            items = list(cart.items.select_for_update().order_by("pk"))
            variants = lock_variants(item.variant_id for item in items)
            priced = price_lines([(variants[item.variant_id], item.quantity) for item in items])
            if priced.has_issues:
                raise ApiError(
                    "بعضی اقلام سبد خرید تغییر کرده‌اند. سبد را بررسی کنید.",
                    code="cart_changed",
                    status_code=409,
                    fields={str(line.variant.pk): line.issue for line in priced.lines if line.issue},
                )

            options = quote_shipping(
                province_id=province.pk if province else None,
                city=cleaned["city"],
                weight_grams=priced.weight_grams,
                merchandise_subtotal=priced.subtotal,
            )
            option = next((o for o in options if o.method.pk == method.pk), None)
            if option is None or not option.available:
                reason = option.unavailable_reason if option else ""
                raise ApiError(
                    reason or "این روش ارسال برای مقصد شما فعال نیست.",
                    code="shipping_unavailable",
                    fields={"shipping_method_id": reason},
                )

            totals = compute_totals(priced, option, store)
            if expected_total is not None and expected_total != totals.grand_total:
                raise ApiError(
                    "مبلغ سفارش تغییر کرده است. مبلغ جدید را بررسی و دوباره تأیید کنید.",
                    code="total_changed",
                    status_code=409,
                    fields={"grand_total": str(totals.grand_total)},
                )

            now = timezone.now()
            order = Order.objects.create(
                idempotency_key=idempotency_key or None,
                user=user if getattr(user, "is_authenticated", False) else None,
                stock_state=Order.StockState.RESERVED,
                reservation_expires_at=now + timedelta(minutes=settings.ORDER_RESERVATION_MINUTES),
                is_test=priced.contains_sample,
                province_name=province.name if province else "",
                shipping_method=method,
                shipping_method_name=method.name,
                shipping_payment_timing=method.payment_timing,
                shipping_estimate=method.delivery_estimate,
                total_weight_grams=priced.weight_grams,
                merchandise_total=totals.merchandise_total,
                discount_total=totals.discount_total,
                tax_total=totals.tax_total,
                shipping_total=totals.shipping_total,
                grand_total=totals.grand_total,
                **cleaned,
            )
            for line in priced.lines:
                variant = line.variant
                variant.stock -= line.quantity
                variant.save(update_fields=["stock", "updated_at"])
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    product_name=variant.product.name,
                    variant_title=variant.title,
                    sku=variant.sku,
                    package_amount=variant.package_amount,
                    package_unit=variant.package_unit,
                    list_unit_price=line.list_unit_price,
                    unit_price=line.unit_price,
                    quantity=line.quantity,
                    line_discount=line.line_discount,
                    line_total=line.line_total,
                    unit_weight_grams=variant.shipping_weight_grams,
                    is_sample_product=variant.product.is_sample,
                )
            OrderEvent.objects.create(
                order=order, kind="placed", message="سفارش ثبت شد و در انتظار پرداخت است.", is_customer_visible=True
            )
            audit("order_placed", order, f"ثبت سفارش {order.number}", actor=user, grand_total=order.grand_total)
            cart.items.all().delete()
            return order
    except IntegrityError as exc:
        # A concurrent retry with the same idempotency key won the race.
        existing = Order.objects.filter(idempotency_key=idempotency_key).first() if idempotency_key else None
        if existing:
            return existing
        raise ApiError(
            "ثبت سفارش ممکن نشد؛ موجودی تغییر کرده است. دوباره تلاش کنید.", code="conflict", status_code=409
        ) from exc
