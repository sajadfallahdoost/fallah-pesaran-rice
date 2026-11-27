"""Application payment service on top of az-iranian-bank-gateways.

Lifecycle (see docs/PAYMENTS.md):
1. `start_payment` creates our PaymentAttempt, asks the library for a gateway session
   (`ready()` → library Bank record) and returns url/method/params for the browser.
2. The provider redirects to the library callback view, which performs the server-to-server
   verify and stores the outcome on its Bank record, then redirects to our return view.
3. `handle_return` reads the persisted Bank record (never the query string), validates
   attempt/provider/amount, and finalizes the order exactly once.
4. `reconcile_attempt` re-runs the library verify only for ambiguous attempts
   (Bank status RETURN_FROM_BANK: verify did not complete).
"""

import copy
import logging
from dataclasses import dataclass
from datetime import timedelta

from azbankgateways.bankfactories import BankFactory
from azbankgateways.exceptions import AZBankGatewaysException
from azbankgateways.models import Bank
from azbankgateways.models import PaymentStatus as BankStatus
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import HttpRequest, QueryDict
from django.utils import timezone

from apps.core.api import ApiError
from apps.core.models import audit
from apps.orders.models import Order, OrderEvent
from apps.orders.services.lifecycle import apply_verified_payment
from apps.payments.models import PaymentAttempt, PaymentProvider

logger = logging.getLogger(__name__)

# A redirected attempt with no callback after this long is treated as abandoned.
ABANDONED_AFTER = timedelta(minutes=20)


@dataclass
class GatewayRedirect:
    url: str
    method: str
    params: dict


def configured_provider_codes() -> set[str]:
    return set(settings.AZ_IRANIAN_BANK_GATEWAYS["GATEWAYS"].keys())


def available_providers() -> list[PaymentProvider]:
    configured = configured_provider_codes()
    return [p for p in PaymentProvider.objects.filter(is_enabled=True) if p.code in configured]


def _bank_status_to_attempt(bank_status: str) -> str:
    return {
        BankStatus.COMPLETE: PaymentAttempt.Status.SUCCEEDED,
        BankStatus.CANCEL_BY_USER: PaymentAttempt.Status.CANCELED,
        BankStatus.ERROR: PaymentAttempt.Status.FAILED,
        BankStatus.EXPIRE_GATEWAY_TOKEN: PaymentAttempt.Status.EXPIRED,
        BankStatus.EXPIRE_VERIFY_PAYMENT: PaymentAttempt.Status.UNKNOWN,
        BankStatus.RETURN_FROM_BANK: PaymentAttempt.Status.UNKNOWN,
        BankStatus.REDIRECT_TO_BANK: PaymentAttempt.Status.REDIRECTED,
        BankStatus.WAITING: PaymentAttempt.Status.CREATED,
    }.get(bank_status, PaymentAttempt.Status.UNKNOWN)


def _request_without_query(request) -> HttpRequest:
    """The library copies the current query string into the gateway callback URL; never leak the order token."""
    clean = copy.copy(getattr(request, "_request", request))
    clean.GET = QueryDict()
    clean.META = {**clean.META, "QUERY_STRING": ""}
    return clean


def start_payment(order: Order, provider_code: str, request) -> GatewayRedirect:
    providers = {p.code: p for p in available_providers()}
    if provider_code not in providers:
        raise ApiError("این درگاه پرداخت در دسترس نیست.", code="provider_unavailable")

    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.payment_status != Order.PaymentStatus.UNPAID:
            raise ApiError("این سفارش قبلاً پرداخت شده است.", code="already_paid", status_code=409)
        if order.status != Order.Status.AWAITING_PAYMENT:
            raise ApiError("مهلت پرداخت این سفارش تمام شده یا سفارش لغو شده است.", code="not_payable", status_code=409)
        if order.reservation_expires_at <= timezone.now():
            raise ApiError(
                "مهلت پرداخت تمام شده است. لطفاً دوباره سفارش دهید.", code="reservation_expired", status_code=409
            )

        pending = list(
            order.payment_attempts.select_for_update().filter(
                status__in=[PaymentAttempt.Status.UNKNOWN, PaymentAttempt.Status.REDIRECTED]
            )
        )

    # Resolve earlier attempts first; never open a second charge while one is ambiguous.
    for attempt in pending:
        sync_attempt(attempt)
        attempt.refresh_from_db()
        if attempt.status == PaymentAttempt.Status.UNKNOWN:
            reconcile_attempt(attempt)
            attempt.refresh_from_db()
        if attempt.status == PaymentAttempt.Status.SUCCEEDED:
            raise ApiError("پرداخت قبلی این سفارش تأیید شده است.", code="already_paid", status_code=409)
        if attempt.status == PaymentAttempt.Status.UNKNOWN:
            raise ApiError(
                "نتیجهٔ پرداخت قبلی هنوز از بانک استعلام نشده است. چند دقیقهٔ دیگر دوباره تلاش کنید.",
                code="previous_payment_pending",
                status_code=409,
            )
        if attempt.status == PaymentAttempt.Status.REDIRECTED:
            # Customer left the gateway without returning; a late callback is still handled.
            attempt.provider_message = "تلاش جدید پرداخت آغاز شد."
            attempt.save(update_fields=["provider_message", "updated_at"])

    attempt = PaymentAttempt.objects.create(
        order=order,
        provider=provider_code,
        amount=order.grand_total,
        currency=order.currency,
        is_test=provider_code == "MOCK",
    )
    callback_url = f"{settings.PUBLIC_BASE_URL}/api/v1/payments/return/?attempt={attempt.public_id}"
    try:
        bank = BankFactory().create(provider_code)
        bank.set_request(_request_without_query(request))
        bank.set_amount(order.grand_total)
        bank.set_client_callback_url(callback_url)
        bank.set_mobile_number(order.phone)
        bank_record = bank.ready()
        gateway = bank.get_gateway()
    except AZBankGatewaysException as exc:
        attempt.status = PaymentAttempt.Status.FAILED
        attempt.provider_message = f"اتصال به درگاه ناموفق بود ({exc.__class__.__name__})."
        attempt.save(update_fields=["status", "provider_message", "updated_at"])
        logger.warning("Gateway session failed for order %s via %s: %s", order.number, provider_code, exc.__class__)
        raise ApiError(
            "اتصال به درگاه پرداخت برقرار نشد. کمی بعد یا با درگاه دیگری تلاش کنید.",
            code="gateway_error",
            status_code=502,
        ) from exc

    attempt.bank_record = bank_record
    attempt.tracking_code = str(bank_record.tracking_code)
    attempt.reference_number = bank_record.reference_number
    attempt.status = PaymentAttempt.Status.REDIRECTED
    attempt.save(update_fields=["bank_record", "tracking_code", "reference_number", "status", "updated_at"])
    OrderEvent.objects.create(order=order, kind="payment_started", message=f"انتقال به درگاه {provider_code}")
    return GatewayRedirect(url=gateway["url"], method=gateway["method"], params=gateway.get("params") or {})


def sync_attempt(attempt: PaymentAttempt) -> PaymentAttempt:
    """Copy the library's persisted verification result onto our attempt and finalize if verified."""
    if attempt.bank_record_id is None:
        return attempt
    with transaction.atomic():
        attempt = PaymentAttempt.objects.select_for_update().get(pk=attempt.pk)
        bank: Bank = Bank.objects.get(pk=attempt.bank_record_id)
        new_status = _bank_status_to_attempt(bank.status)

        if attempt.status in (PaymentAttempt.Status.SUCCEEDED, PaymentAttempt.Status.MISMATCH):
            succeeded = attempt.status == PaymentAttempt.Status.SUCCEEDED and not attempt.applied_to_order
        else:
            succeeded = False
            if new_status == PaymentAttempt.Status.SUCCEEDED:
                problems = []
                if str(bank.tracking_code) != attempt.tracking_code:
                    problems.append("tracking_code")
                if bank.bank_type != attempt.provider:
                    problems.append("provider")
                if int(bank.amount) != attempt.amount:
                    problems.append("amount")
                if problems:
                    attempt.status = PaymentAttempt.Status.MISMATCH
                    attempt.provider_message = "مغایرت: " + "، ".join(problems)
                    order = Order.objects.select_for_update().get(pk=attempt.order_id)
                    order.needs_review = True
                    order.review_reason = "مغایرت در نتیجهٔ پرداخت؛ تطبیق دستی لازم است."
                    order.save(update_fields=["needs_review", "review_reason", "updated_at"])
                    audit("payment_mismatch", order, attempt.provider_message, attempt=str(attempt.public_id))
                else:
                    attempt.status = PaymentAttempt.Status.SUCCEEDED
                    attempt.verified_at = timezone.now()
                    if attempt.provider == "ZARINPAL" and (bank.response_result or "").isdigit():
                        attempt.reference_number = bank.response_result
                    else:
                        attempt.reference_number = bank.reference_number
                    succeeded = True
            else:
                attempt.status = new_status
            attempt.provider_message = attempt.provider_message or (bank.response_result or "")[:255]
            attempt.save()

    if succeeded:
        apply_verified_payment(attempt.order_id, attempt)
        attempt.refresh_from_db()
    return attempt


def handle_return(attempt_public_id: str, tracking_code: str) -> PaymentAttempt | None:
    attempt = PaymentAttempt.objects.filter(public_id=attempt_public_id).select_related("order").first()
    if attempt is None:
        return None
    if tracking_code and attempt.tracking_code == tracking_code:
        PaymentAttempt.objects.filter(pk=attempt.pk).update(callback_count=F("callback_count") + 1)
        return sync_attempt(attempt)
    return attempt


def reconcile_attempt(attempt: PaymentAttempt) -> PaymentAttempt:
    """Ask the provider again (through the library) for an attempt whose verify did not complete."""
    if attempt.bank_record_id is None:
        return attempt
    bank_record = Bank.objects.get(pk=attempt.bank_record_id)
    if bank_record.status == BankStatus.RETURN_FROM_BANK:
        try:
            bank = BankFactory().create(bank_record.bank_type)
            bank.verify(bank_record.tracking_code)
        except AZBankGatewaysException as exc:
            logger.warning("Reconciliation verify failed for attempt %s: %s", attempt.public_id, exc.__class__)
    elif (
        bank_record.status in (BankStatus.REDIRECT_TO_BANK, BankStatus.WAITING)
        and timezone.now() - bank_record.created_at > ABANDONED_AFTER
    ):
        PaymentAttempt.objects.filter(
            pk=attempt.pk, status__in=[PaymentAttempt.Status.CREATED, PaymentAttempt.Status.REDIRECTED]
        ).update(status=PaymentAttempt.Status.EXPIRED, provider_message="مشتری از درگاه بازنگشت.")
        attempt.refresh_from_db()
        return attempt
    return sync_attempt(attempt)
