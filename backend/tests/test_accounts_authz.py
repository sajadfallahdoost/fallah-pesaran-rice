import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client

from apps.accounts.models import OtpCode
from apps.core.roles import CATALOG_EDITOR, ORDER_OPERATOR, OWNER
from apps.orders.models import Order
from tests.conftest import Shopper

pytestmark = pytest.mark.django_db


@pytest.fixture
def sms(monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr("apps.accounts.services.send_otp", lambda phone, code: sent.append((phone, code)))
    return sent


def login(shopper: Shopper, sms, phone="09121111111"):
    assert shopper.post("/auth/otp/request/", {"phone": phone}).status_code == 200
    code = sms[-1][1]
    response = shopper.post("/auth/otp/verify/", {"phone": phone, "code": code})
    assert response.status_code == 200, response.json()
    return code


def test_otp_is_hashed_single_use_and_attempt_limited(seeded, shopper, sms):
    shopper.post("/auth/otp/request/", {"phone": "۰۹۱۲۱۱۱۱۱۱۱"})
    phone, code = sms[-1]
    assert phone == "09121111111"
    otp = OtpCode.objects.get()
    assert code not in otp.code_hash

    wrong = "00000" if code != "00000" else "11111"
    for _ in range(5):
        assert shopper.post("/auth/otp/verify/", {"phone": phone, "code": wrong}).status_code == 400
    blocked = shopper.post("/auth/otp/verify/", {"phone": phone, "code": code})
    assert blocked.status_code == 429  # correct code no longer accepted after 5 failures


def test_otp_cooldown_and_login_merges_guest_cart(seeded, shopper, sms):
    shopper.add("FS-TEA-01-500", 2)
    login(shopper, sms)
    assert shopper.post("/auth/otp/request/", {"phone": "09121111111"}).status_code == 429  # 60 s cooldown
    me = shopper.get("/auth/me/").json()
    assert me == {"authenticated": True, "phone": "09121111111"}
    assert shopper.get("/cart/").json()["item_count"] == 2
    user = get_user_model().objects.get(username="09121111111")
    assert not user.has_usable_password() and not user.is_staff


def test_code_cannot_be_reused(seeded, shopper, sms):
    code = login(shopper, sms)
    other = Shopper(Client())
    assert other.post("/auth/otp/verify/", {"phone": "09121111111", "code": code}).status_code == 400


def test_staff_cannot_login_with_otp(seeded, shopper, sms):
    get_user_model().objects.create_user(username="09122222222", password="x-strong-pass-1", is_staff=True)
    shopper.post("/auth/otp/request/", {"phone": "09122222222"})
    response = shopper.post("/auth/otp/verify/", {"phone": "09122222222", "code": sms[-1][1]})
    assert response.status_code == 403


def test_order_access_requires_owner_or_token(seeded, shopper, sms):
    shopper.add("FS-RICE-01-5")
    order = shopper.checkout()
    number, token = order["number"], order["token"]
    stranger = Shopper(Client())
    assert stranger.get(f"/orders/{number}/").status_code == 404
    assert stranger.get(f"/orders/{number}/?t=wrong").status_code == 404
    assert stranger.get(f"/orders/{number}/invoice.pdf").status_code == 404
    assert stranger.post(f"/orders/{number}/pay/", {"provider": "MOCK"}).status_code == 404
    assert stranger.get(f"/orders/{number}/?t={token}").status_code == 200


def test_tracking_needs_matching_phone_and_hides_private_data(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    number = shopper.checkout()["number"]
    stranger = Shopper(Client())
    assert stranger.post("/orders/track/", {"number": number, "phone": "09129999999"}).status_code == 404
    data = stranger.post("/orders/track/", {"number": number.lower(), "phone": "۰۹۱۲۰۰۰۰۰۰۱"}).json()
    assert data["number"] == number
    for private in ("address_line", "full_name", "phone", "postal_code", "grand_total"):
        assert private not in data


def test_account_orders_and_addresses_are_isolated(seeded, sms):
    alice, bob = Shopper(Client()), Shopper(Client())
    login(alice, sms, "09121111111")
    alice.add("FS-RICE-01-5")
    number = alice.checkout(save_address=True)["number"]
    login(bob, sms, "09123333333")

    assert [o["number"] for o in alice.get("/account/orders/").json()] == [number]
    assert bob.get("/account/orders/").json() == []
    assert bob.get(f"/account/orders/{number}/").status_code == 404
    assert bob.get(f"/orders/{number}/").status_code == 404

    address = alice.get("/account/addresses/").json()[0]
    assert bob.client.delete(f"/api/v1/account/addresses/{address['id']}/").status_code == 404
    assert alice.client.delete(f"/api/v1/account/addresses/{address['id']}/").status_code == 204


def _staff(role: str) -> Client:
    user = get_user_model().objects.create_user(username=f"staff-{role}", password="x-strong-pass-1", is_staff=True)
    user.groups.add(Group.objects.get(name=role))
    client = Client()
    client.force_login(user)
    return client


def _paid_order(shopper: Shopper) -> Order:
    shopper.add("FS-RICE-01-5")
    order = shopper.checkout()
    shopper.pay(order["number"], order["token"], "paid")
    return Order.objects.get(number=order["number"])


def test_role_permissions_on_reports_and_operations(seeded, shopper):
    order = _paid_order(shopper)
    owner, operator, editor = _staff(OWNER), _staff(ORDER_OPERATOR), _staff(CATALOG_EDITOR)

    assert owner.get("/admin/reports/").status_code == 200
    assert operator.get("/admin/reports/").status_code == 403
    assert editor.get("/admin/reports/").status_code == 403
    assert operator.get("/admin/reports/export/orders.csv").status_code == 403

    url = f"/admin/orders/order/{order.pk}/operate/"
    assert editor.post(url + "preparing/").status_code in (302, 403)
    order.refresh_from_db()
    assert order.fulfillment_status == Order.FulfillmentStatus.UNFULFILLED

    operator.post(url + "preparing/")
    order.refresh_from_db()
    assert order.fulfillment_status == Order.FulfillmentStatus.PREPARING

    assert operator.post(url + "refund/", {"amount": "1000", "reason": "x"}).status_code == 403
    assert operator.post(url + "cancel/", {"reason": "x"}).status_code == 403
    order.refresh_from_db()
    assert order.status == Order.Status.CONFIRMED and not order.refunds.exists()


def test_no_mark_paid_path_in_admin(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    order = Order.objects.get(number=shopper.checkout()["number"])
    owner = _staff(OWNER)
    response = owner.post(f"/admin/orders/order/{order.pk}/change/", {"payment_status": "paid", "status": "confirmed"})
    assert response.status_code in (200, 302, 403)
    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.UNPAID
    assert owner.post(f"/admin/orders/order/{order.pk}/operate/mark_paid/").status_code == 403
    assert owner.get("/admin/azbankgateways/bank/add/").status_code == 403


def test_customer_cannot_reach_admin(seeded, shopper, sms):
    login(shopper, sms)
    response = shopper.client.get("/admin/")
    assert response.status_code == 302 and "/admin/login/" in response["Location"]
