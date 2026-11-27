"""Order state transitions after checkout: payment application, expiry, fulfillment,
cancellation, and refunds. Each transition locks the order row first."""

from datetime import timedelta

import jdatetime
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.api import ApiError
from apps.core.models import audit
from apps.orders.models import Invoice, Order, OrderEvent, Refund, Shipment
from apps.orders.services.inventory import release_reservation, try_reserve_again

# An order is not expired while a payment attempt is younger than this (customer may be on the gateway).
PAYMENT_IN_FLIGHT_GRACE = timedelta(minutes=20)


def lock_order(order_id: int) -> Order:
    return Order.objects.select_for_update().get(pk=order_id)


def _event(order: Order, kind: str, message: str, actor=None, visible: bool = False) -> None:
    OrderEvent.objects.create(order=order, kind=kind, message=message, actor=actor, is_customer_visible=visible)


def _flag(order: Order, reason: str) -> None:
    order.needs_review = True
    order.review_reason = reason[:255]


def issue_invoice(order: Order) -> Invoice:
    invoice = Invoice.objects.filter(order=order).first()
    if invoice:
        return invoice
    year = jdatetime.date.fromgregorian(date=timezone.localdate()).year
    invoice = Invoice.objects.create(order=order, number=f"tmp-{order.pk}")
    invoice.number = f"R{year}-{invoice.pk:06d}"
    invoice.save(update_fields=["number"])
    return invoice


@transaction.atomic
def apply_verified_payment(order_id: int, attempt) -> str:
    """Finalize an order for a verified, amount-checked payment attempt. Exactly-once.

    Returns one of: "applied", "already_applied", "duplicate", "after_cancel".
    """
    order = lock_order(order_id)
    attempt.refresh_from_db()
    if attempt.applied_to_order:
        return "already_applied"

    if order.payment_status != Order.PaymentStatus.UNPAID:
        _flag(order, f"پرداخت تکراری با درگاه {attempt.provider}؛ مبلغ اضافه باید بازپرداخت شود.")
        order.save(update_fields=["needs_review", "review_reason", "updated_at"])
        _event(order, "duplicate_payment", f"پرداخت تأییدشدهٔ اضافه ({attempt.reference_number}) نیازمند بازپرداخت است.")
        audit("duplicate_payment", order, "پرداخت تکراری", attempt=str(attempt.public_id), amount=attempt.amount)
        return "duplicate"

    if order.status == Order.Status.CANCELED:
        _flag(order, "پرداخت پس از لغو سفارش دریافت شد؛ بازپرداخت یا احیای سفارش را بررسی کنید.")
        order.save(update_fields=["needs_review", "review_reason", "updated_at"])
        _event(order, "payment_after_cancel", "پرداخت پس از لغو سفارش دریافت شد.")
        audit("payment_after_cancel", order, "پرداخت پس از لغو", attempt=str(attempt.public_id))
        return "after_cancel"

    now = timezone.now()
    if attempt.provider == "ZARINPAL" and attempt.is_test:
        if order.stock_state == Order.StockState.RESERVED:
            release_reservation(order, "آزادسازی موجودی پرداخت آزمایشی")
    elif order.stock_state == Order.StockState.RELEASED and not try_reserve_again(order):
        _flag(order, "پرداخت پس از پایان رزرو انجام شد و موجودی کافی نیست؛ تأمین کالا یا بازپرداخت لازم است.")
        _event(order, "late_payment_no_stock", "پرداخت دیرهنگام بدون موجودی کافی؛ نیازمند بررسی فروشگاه.")
    else:
        order.refresh_from_db(fields=["stock_state"])
        order.stock_state = Order.StockState.COMMITTED

    order.status = Order.Status.CONFIRMED
    order.payment_status = Order.PaymentStatus.PAID
    order.paid_at = now
    order.is_test = order.is_test or attempt.is_test
    order.save()

    attempt.applied_to_order = True
    attempt.save(update_fields=["applied_to_order", "updated_at"])
    issue_invoice(order)
    _event(order, "paid", "پرداخت تأیید شد. سفارش برای آماده‌سازی ثبت شد.", visible=True)
    audit("order_paid", order, f"پرداخت سفارش {order.number}", attempt=str(attempt.public_id), amount=attempt.amount)
    return "applied"


@transaction.atomic
def expire_order_if_due(order_id: int, now=None) -> bool:
    now = now or timezone.now()
    order = lock_order(order_id)
    if order.status != Order.Status.AWAITING_PAYMENT or order.reservation_expires_at > now:
        return False
    if order.payment_attempts.filter(created_at__gt=now - PAYMENT_IN_FLIGHT_GRACE).exists():
        return False
    release_reservation(order, "پایان مهلت پرداخت")
    order.status = Order.Status.EXPIRED
    order.save(update_fields=["status", "updated_at"])
    _event(order, "expired", "مهلت پرداخت تمام شد و رزرو کالا آزاد شد.", visible=True)
    return True


@transaction.atomic
def cancel_order(order_id: int, reason: str, actor=None) -> Order:
    order = lock_order(order_id)
    if order.status in (Order.Status.CANCELED, Order.Status.EXPIRED):
        raise ApiError("این سفارش قبلاً بسته شده است.", code="invalid_transition")
    if order.fulfillment_status in (Order.FulfillmentStatus.SHIPPED, Order.FulfillmentStatus.DELIVERED):
        raise ApiError("سفارش ارسال‌شده لغو نمی‌شود؛ از مسیر مرجوعی و بازپرداخت استفاده کنید.", code="invalid_transition")
    if not reason.strip():
        raise ApiError("علت لغو را بنویسید.", code="reason_required")

    if order.stock_state != Order.StockState.RELEASED:
        release_reservation(order, f"لغو سفارش: {reason}", actor=actor)
    order.status = Order.Status.CANCELED
    order.canceled_at = timezone.now()
    order.cancel_reason = reason[:255]
    if order.is_paid:
        _flag(order, "سفارش پرداخت‌شده لغو شد؛ بازپرداخت را ثبت و پیگیری کنید.")
    order.save()
    _event(order, "canceled", f"سفارش لغو شد: {reason}", actor=actor, visible=True)
    audit("order_canceled", order, reason, actor=actor, was_paid=order.is_paid)
    return order


_FULFILLMENT_FLOW = {
    Order.FulfillmentStatus.UNFULFILLED: {Order.FulfillmentStatus.PREPARING},
    Order.FulfillmentStatus.PREPARING: {Order.FulfillmentStatus.SHIPPED},
    Order.FulfillmentStatus.SHIPPED: {Order.FulfillmentStatus.DELIVERED, Order.FulfillmentStatus.RETURNED},
    Order.FulfillmentStatus.DELIVERED: {Order.FulfillmentStatus.RETURNED},
    Order.FulfillmentStatus.RETURNED: set(),
}

_CUSTOMER_MESSAGES = {
    Order.FulfillmentStatus.PREPARING: "سفارش در حال آماده‌سازی است.",
    Order.FulfillmentStatus.SHIPPED: "سفارش ارسال شد.",
    Order.FulfillmentStatus.DELIVERED: "سفارش تحویل شد.",
    Order.FulfillmentStatus.RETURNED: "مرسوله مرجوع شد.",
}


@transaction.atomic
def advance_fulfillment(
    order_id: int, target: str, actor=None, carrier: str = "", tracking_code: str = "", tracking_url: str = "", note=""
) -> Order:
    order = lock_order(order_id)
    if order.status != Order.Status.CONFIRMED or not order.is_paid:
        raise ApiError("فقط سفارش پرداخت‌شده و تأییدشده قابل ارسال است.", code="invalid_transition")
    if order.stock_state != Order.StockState.COMMITTED:
        raise ApiError("موجودی این سفارش قطعی نشده است؛ ابتدا مورد بررسی را حل کنید.", code="stock_not_committed")
    if target not in _FULFILLMENT_FLOW.get(order.fulfillment_status, set()):
        raise ApiError("این تغییر وضعیت مجاز نیست.", code="invalid_transition")

    now = timezone.now()
    shipment = order.shipments.order_by("-created_at").first()
    if target == Order.FulfillmentStatus.PREPARING:
        shipment = Shipment.objects.create(
            order=order, status=Shipment.Status.PREPARING, carrier=order.shipping_method_name
        )
    else:
        if shipment is None:
            shipment = Shipment.objects.create(order=order, carrier=order.shipping_method_name)
        if target == Order.FulfillmentStatus.SHIPPED:
            shipment.status = Shipment.Status.SHIPPED
            shipment.shipped_at = now
            shipment.carrier = carrier or shipment.carrier
            shipment.tracking_code = tracking_code or shipment.tracking_code
            shipment.tracking_url = tracking_url or shipment.tracking_url
        elif target == Order.FulfillmentStatus.DELIVERED:
            shipment.status = Shipment.Status.DELIVERED
            shipment.delivered_at = now
        elif target == Order.FulfillmentStatus.RETURNED:
            shipment.status = Shipment.Status.RETURNED
        if note:
            shipment.note = note[:255]
        shipment.save()

    order.fulfillment_status = target
    order.save(update_fields=["fulfillment_status", "updated_at"])
    message = _CUSTOMER_MESSAGES[target]
    if target == Order.FulfillmentStatus.SHIPPED and shipment.tracking_code:
        message += f" کد رهگیری: {shipment.tracking_code}"
    _event(order, f"fulfillment_{target}", message, actor=actor, visible=True)
    audit("fulfillment", order, message, actor=actor, target=target)
    return order


def refundable_amount(order: Order) -> int:
    committed = order.refunds.exclude(status=Refund.Status.REJECTED).aggregate(total=Sum("amount"))["total"] or 0
    return max(0, order.grand_total - committed)


@transaction.atomic
def request_refund(order_id: int, amount: int, reason: str, restock: bool, actor) -> Refund:
    order = lock_order(order_id)
    if not order.is_paid:
        raise ApiError("برای سفارش پرداخت‌نشده بازپرداخت معنا ندارد.", code="not_paid")
    if amount <= 0 or amount % 10:
        raise ApiError("مبلغ بازپرداخت باید مثبت و مضرب ۱۰ ریال باشد.", code="invalid_amount")
    available = refundable_amount(order)
    if amount > available:
        raise ApiError(f"حداکثر مبلغ قابل بازپرداخت {available} ریال است.", code="amount_exceeds")
    if restock and amount != order.grand_total:
        raise ApiError("بازگشت کالا به موجودی فقط با بازپرداخت کامل سفارش ثبت می‌شود.", code="restock_requires_full")
    if not reason.strip():
        raise ApiError("علت بازپرداخت را بنویسید.", code="reason_required")
    refund = Refund.objects.create(order=order, amount=amount, reason=reason, restock=restock, created_by=actor)
    _event(order, "refund_requested", f"درخواست بازپرداخت {amount} ریال ثبت شد.", actor=actor)
    audit("refund_requested", order, reason, actor=actor, amount=amount, refund=refund.pk)
    return refund


@transaction.atomic
def set_refund_status(refund_id: int, target: str, actor, external_reference: str = "") -> Refund:
    refund = Refund.objects.select_for_update().get(pk=refund_id)
    order = lock_order(refund.order_id)
    allowed = {
        Refund.Status.REQUESTED: {Refund.Status.APPROVED, Refund.Status.REJECTED},
        Refund.Status.APPROVED: {Refund.Status.COMPLETED, Refund.Status.REJECTED},
    }
    if target not in allowed.get(refund.status, set()):
        raise ApiError("این تغییر وضعیت بازپرداخت مجاز نیست.", code="invalid_transition")
    if target == Refund.Status.COMPLETED:
        if not external_reference.strip():
            raise ApiError("برای ثبت واریز، مرجع بانکی الزامی است.", code="reference_required")
        refund.external_reference = external_reference.strip()[:80]
        refund.completed_at = timezone.now()
    refund.status = target
    refund.save()

    if target == Refund.Status.COMPLETED:
        refunded = order.refunds.filter(status=Refund.Status.COMPLETED).aggregate(t=Sum("amount"))["t"] or 0
        order.payment_status = (
            Order.PaymentStatus.REFUNDED if refunded >= order.grand_total else Order.PaymentStatus.PARTIALLY_REFUNDED
        )
        order.save(update_fields=["payment_status", "updated_at"])
        if refund.restock and order.stock_state == Order.StockState.COMMITTED:
            release_reservation(order, "بازگشت کالا به موجودی پس از بازپرداخت", actor=actor)
    _event(order, f"refund_{target}", f"بازپرداخت {refund.amount} ریال: {refund.get_status_display()}", actor=actor)
    audit("refund_status", order, refund.get_status_display(), actor=actor, refund=refund.pk, target=target)
    return refund
