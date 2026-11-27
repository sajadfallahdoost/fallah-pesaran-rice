from datetime import timedelta
from unittest.mock import Mock
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from azbankgateways.models import Bank
from django.core.management import call_command
from django.utils import timezone

from apps.orders.models import Order
from apps.payments.models import MockGatewayDecision, PaymentAttempt, PaymentProvider
from tests.conftest import variant

pytestmark = pytest.mark.django_db


@pytest.fixture
def placed(seeded, shopper):
    shopper.add("FS-RICE-01-5", 2)
    order = shopper.checkout()
    return shopper, order["number"], order["token"]


def _order(number) -> Order:
    return Order.objects.get(number=number)


def test_successful_payment_confirms_order_once(placed):
    shopper, number, token = placed
    result, query, _ = shopper.pay(number, token, "paid")
    assert result.path == f"/checkout/result/{number}"
    assert query["t"] == token

    order = _order(number)
    assert order.status == Order.Status.CONFIRMED
    assert order.payment_status == Order.PaymentStatus.PAID
    assert order.stock_state == Order.StockState.COMMITTED
    assert order.paid_at is not None
    assert order.invoice.number.startswith("R")
    attempt = order.payment_attempts.get()
    assert attempt.status == PaymentAttempt.Status.SUCCEEDED and attempt.applied_to_order
    assert variant("FS-RICE-01-5").stock == 23  # reserved at checkout, not decremented again

    detail = shopper.order(number, token)
    assert detail["stage"] == "confirmed" or detail["status"] == "confirmed"
    assert detail["latest_payment"]["reference_number"]
    assert shopper.get(f"/orders/{number}/invoice.pdf?t={token}").status_code == 200


def test_gateway_never_receives_order_token(placed):
    shopper, number, token = placed
    gateway = shopper.start_payment(number, token).json()
    assert token not in str(gateway)
    assert "t=" not in urlparse(gateway["params"]["callback"]).query


@pytest.mark.parametrize(
    ("decision", "attempt_status"),
    [("canceled", PaymentAttempt.Status.CANCELED), ("failed", PaymentAttempt.Status.FAILED)],
)
def test_unsuccessful_payment_keeps_order_payable(placed, decision, attempt_status):
    shopper, number, token = placed
    shopper.pay(number, token, decision)
    order = _order(number)
    assert order.status == Order.Status.AWAITING_PAYMENT
    assert order.payment_status == Order.PaymentStatus.UNPAID
    assert order.payment_attempts.get().status == attempt_status
    assert not hasattr(order, "invoice") or order.invoice is None
    assert shopper.get(f"/orders/{number}/invoice.pdf?t={token}").status_code == 404
    # Retry succeeds with a new attempt.
    shopper.pay(number, token, "paid")
    assert _order(number).payment_status == Order.PaymentStatus.PAID
    assert _order(number).payment_attempts.count() == 2


def test_tampered_return_query_cannot_mark_paid(placed):
    shopper, number, token = placed
    gateway = shopper.start_payment(number, token).json()
    attempt = PaymentAttempt.objects.get(order__number=number)
    # Attacker skips the gateway and hits our return URL directly with a guessed tracking code.
    response = shopper.client.get(
        "/api/v1/payments/return/", {"attempt": str(attempt.public_id), "tc": attempt.tracking_code, "status": "OK"}
    )
    assert response.status_code == 302
    assert _order(number).payment_status == Order.PaymentStatus.UNPAID
    # Hitting the library callback without a gateway decision is treated as cancel, not success.
    callback = urlparse(gateway["params"]["callback"])
    shopper.client.get(
        callback.path, {**{k: v[0] for k, v in parse_qs(callback.query).items()}, "ref": gateway["params"]["ref"]}
    )
    assert _order(number).payment_status == Order.PaymentStatus.UNPAID


def test_repeated_callback_is_idempotent(placed):
    shopper, number, token = placed
    gateway = shopper.start_payment(number, token).json()
    callback = shopper.gateway_decision(gateway, "paid")
    shopper.follow_callback(callback)
    shopper.follow_callback(callback)  # browser refresh / provider retry
    order = _order(number)
    assert order.payment_status == Order.PaymentStatus.PAID
    assert order.payment_attempts.filter(applied_to_order=True).count() == 1
    assert order.events.filter(kind="paid").count() == 1
    assert variant("FS-RICE-01-5").stock == 23


def test_amount_mismatch_flags_review_and_does_not_confirm(placed):
    shopper, number, token = placed
    gateway = shopper.start_payment(number, token).json()
    attempt = PaymentAttempt.objects.get(order__number=number)
    Bank.objects.filter(pk=attempt.bank_record_id).update(amount=str(attempt.amount - 1_000_000))
    shopper.follow_callback(shopper.gateway_decision(gateway, "paid"))
    order = _order(number)
    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.MISMATCH
    assert order.payment_status == Order.PaymentStatus.UNPAID
    assert order.needs_review


def test_timeout_then_reconciliation_applies_payment(placed):
    shopper, number, token = placed
    gateway = shopper.start_payment(number, token).json()
    shopper.follow_callback(shopper.gateway_decision(gateway, "timeout"))
    attempt = PaymentAttempt.objects.get(order__number=number)
    assert attempt.status == PaymentAttempt.Status.UNKNOWN
    assert _order(number).payment_status == Order.PaymentStatus.UNPAID

    # A new payment must not start while the previous result is unknown.
    blocked = shopper.start_payment(number, token)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "previous_payment_pending"

    # The provider later confirms the money was taken; the maintenance job reconciles it.
    MockGatewayDecision.objects.filter(reference_number=attempt.reference_number).update(decision="paid")
    PaymentAttempt.objects.filter(pk=attempt.pk).update(created_at=timezone.now() - timedelta(minutes=15))
    call_command("maintain_orders", stdout=open("/dev/null", "w"))  # noqa: SIM115
    order = _order(number)
    assert order.payment_status == Order.PaymentStatus.PAID
    assert order.status == Order.Status.CONFIRMED


def test_expiry_releases_stock_and_late_payment_reclaims_it(placed):
    shopper, number, token = placed
    gateway = shopper.start_payment(number, token).json()
    callback = shopper.gateway_decision(gateway, "paid")  # decision made, callback not yet delivered
    past = timezone.now() - timedelta(hours=2)
    Order.objects.filter(number=number).update(reservation_expires_at=past)
    PaymentAttempt.objects.filter(order__number=number).update(created_at=past)
    Bank.objects.filter(pk=PaymentAttempt.objects.get(order__number=number).bank_record_id).update(created_at=past)
    call_command("maintain_orders", stdout=open("/dev/null", "w"))  # noqa: SIM115
    order = _order(number)
    assert order.status == Order.Status.EXPIRED
    assert variant("FS-RICE-01-5").stock == 25

    shopper.follow_callback(callback)  # late but verified payment
    order = _order(number)
    assert order.payment_status == Order.PaymentStatus.PAID
    assert order.status == Order.Status.CONFIRMED
    assert order.stock_state == Order.StockState.COMMITTED
    assert variant("FS-RICE-01-5").stock == 23


def test_late_payment_without_stock_needs_review(placed):
    shopper, number, token = placed
    gateway = shopper.start_payment(number, token).json()
    callback = shopper.gateway_decision(gateway, "paid")
    past = timezone.now() - timedelta(hours=2)
    Order.objects.filter(number=number).update(reservation_expires_at=past)
    PaymentAttempt.objects.filter(order__number=number).update(created_at=past)
    Bank.objects.filter(pk=PaymentAttempt.objects.get(order__number=number).bank_record_id).update(created_at=past)
    call_command("maintain_orders", stdout=open("/dev/null", "w"))  # noqa: SIM115
    variant("FS-RICE-01-5").__class__.objects.filter(sku="FS-RICE-01-5").update(stock=0)

    shopper.follow_callback(callback)
    order = _order(number)
    assert order.payment_status == Order.PaymentStatus.PAID  # money was taken: never hide it
    assert order.needs_review
    assert order.stock_state != Order.StockState.COMMITTED
    assert variant("FS-RICE-01-5").stock == 0


def test_second_successful_payment_is_flagged_not_applied(placed):
    shopper, number, token = placed
    first = shopper.start_payment(number, token).json()
    second = shopper.start_payment(number, token).json()  # e.g. two tabs
    first_cb = shopper.gateway_decision(first, "paid")
    second_cb = shopper.gateway_decision(second, "paid")
    shopper.follow_callback(first_cb)
    shopper.follow_callback(second_cb)
    order = _order(number)
    assert order.payment_attempts.filter(status=PaymentAttempt.Status.SUCCEEDED).count() == 2
    assert order.payment_attempts.filter(applied_to_order=True).count() == 1
    assert order.needs_review  # duplicate charge must be refunded by the owner


def test_paid_order_cannot_start_another_payment(placed):
    shopper, number, token = placed
    shopper.pay(number, token, "paid")
    response = shopper.start_payment(number, token)
    assert response.status_code == 409


def test_mock_gateway_disabled_returns_404(placed, settings):
    shopper, number, token = placed
    settings.PAYMENT_MOCK_ENABLED = False
    assert (
        shopper.client.get(
            "/payments/mock-gateway/", {"ref": "MOCK-x", "callback": "/bankgateways/callback/"}
        ).status_code
        == 404
    )


def test_mock_gateway_refuses_foreign_callback(seeded, client):
    response = client.get("/payments/mock-gateway/", {"ref": "MOCK-1", "callback": "https://evil.example/steal"})
    assert response.status_code == 400


def test_unknown_provider_rejected(placed):
    shopper, number, token = placed
    response = shopper.start_payment(number, token, provider="ZARINPAL")  # not configured in tests
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "provider_unavailable"


def test_zarinpal_cancel_failure_and_paid_retry(placed, settings, monkeypatch):
    shopper, number, token = placed
    assert settings.CLASS["ZARINPAL"] == "apps.payments.banks.Zarinpal"
    settings.PUBLIC_BASE_URL = "https://shop.test"
    settings.AZ_IRANIAN_BANK_GATEWAYS = {
        **settings.AZ_IRANIAN_BANK_GATEWAYS,
        "GATEWAYS": {"ZARINPAL": {"MERCHANT_CODE": "00000000-0000-0000-0000-000000000000", "SANDBOX": 0}},
    }
    monkeypatch.setattr("azbankgateways.default_settings.BANK_GATEWAYS", settings.AZ_IRANIAN_BANK_GATEWAYS["GATEWAYS"])
    PaymentProvider.objects.filter(code="ZARINPAL").update(is_enabled=True)
    order = _order(number)
    callbacks = []
    verification_codes = iter((-51, 100))
    verify_requests = []

    def gateway_request(url, *, json, timeout):
        assert type(json["amount"]) is int and json["amount"] == order.grand_total
        assert url.startswith("https://payment.zarinpal.com/pg/v4/payment/")
        if url.endswith("/request.json"):
            authority = "A" + str(len(callbacks) + 1).zfill(35)
            callback = json["callback_url"]
            assert callback.startswith("https://testserver/bankgateways/callback/")
            assert token not in callback
            assert json["currency"] == "IRR"
            callbacks.append(f"{callback}&{urlencode({'Authority': authority})}")
            payload = {"data": {"code": 100, "authority": authority}}
        else:
            verify_requests.append(json["authority"])
            code = next(verification_codes)
            payload = {"data": {"code": code, "ref_id": 123456789} if code == 100 else []}
        return Mock(status_code=200, json=Mock(return_value=payload))

    monkeypatch.setattr("apps.payments.banks.requests.post", gateway_request)
    for callback_status, expected in [
        ("NOK", PaymentAttempt.Status.CANCELED),
        ("OK", PaymentAttempt.Status.FAILED),
        ("OK", PaymentAttempt.Status.SUCCEEDED),
    ]:
        result = shopper.client.post(
            f"/api/v1/orders/{number}/pay/?t={token}",
            {"provider": "ZARINPAL"},
            content_type="application/json",
            secure=True,
        )
        assert result.status_code == 200, result.json()
        assert result.json()["url"].startswith("https://payment.zarinpal.com/pg/StartPay/A")
        callback = f"{callbacks[-1]}&Status={callback_status}"
        shopper.follow_callback(callback)
        assert order.payment_attempts.order_by("-pk").first().status == expected
    shopper.follow_callback(callback)
    order.refresh_from_db()
    assert len(verify_requests) == 2
    assert order.payment_status == Order.PaymentStatus.PAID
    assert order.payment_attempts.get(applied_to_order=True).reference_number == "123456789"
    assert order.events.filter(kind="paid").count() == 1
    assert variant("FS-RICE-01-5").stock == 23
