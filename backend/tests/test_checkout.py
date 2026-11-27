import pytest
from django.test import Client

from apps.core.models import StoreSettings
from apps.orders.models import Order
from tests.conftest import Shopper, variant

pytestmark = pytest.mark.django_db


def test_anonymous_unsafe_requests_require_csrf(seeded):
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        "/api/v1/cart/items/",
        {"variant_id": variant("FS-RICE-01-5").pk, "quantity": 1},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"

    client.get("/api/v1/csrf/")
    token = client.cookies["csrftoken"].value
    response = client.post(
        "/api/v1/cart/items/",
        {"variant_id": variant("FS-RICE-01-5").pk, "quantity": 1},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200


def test_checkout_prices_come_from_server_not_client(seeded, shopper):
    shopper.add("FS-RICE-01-10", 2)
    payload = shopper.checkout_payload(grand_total=1, unit_price=10, discount_total=999_999_999)
    order = shopper.post("/checkout/", payload).json()
    o = Order.objects.get(number=order["number"])
    assert o.merchandise_total == 68_000_000
    assert o.discount_total == 2_200_000
    assert o.grand_total == 65_800_000  # free post shipping above 5,000,000 toman
    assert o.items.get().unit_price == 32_900_000


def test_expected_total_mismatch_is_rejected(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    response = shopper.post("/checkout/", shopper.checkout_payload(expected_total=1))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "total_changed"
    assert response.json()["error"]["fields"]["grand_total"] == "19400000"
    assert not Order.objects.exists()


def test_price_change_after_adding_to_cart_is_reported(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    quote = shopper.post("/checkout/quote/", {}).json()
    old_total = quote["cart"]["subtotal"]
    v = variant("FS-RICE-01-5")
    v.price = 18_000_000
    v.save()
    cart = shopper.get("/cart/").json()
    assert cart["lines"][0]["price_changed_from"] == old_total
    response = shopper.post("/checkout/", shopper.checkout_payload(expected_total=old_total + 1_900_000))
    assert response.status_code == 409


def test_checkout_reserves_stock_and_empties_cart(seeded, shopper):
    shopper.add("FS-RICE-01-5", 3)
    order = shopper.checkout()
    assert variant("FS-RICE-01-5").stock == 22
    o = Order.objects.get(number=order["number"])
    assert o.stock_state == Order.StockState.RESERVED
    assert o.status == Order.Status.AWAITING_PAYMENT
    assert shopper.get("/cart/").json()["item_count"] == 0


def test_cannot_add_more_than_stock_or_out_of_stock(seeded, shopper):
    response = shopper.post("/cart/items/", {"variant_id": variant("FS-TEA-01-1000").pk, "quantity": 5})
    assert response.status_code == 409
    response = shopper.post("/cart/items/", {"variant_id": variant("FS-OIL-01-1000").pk, "quantity": 1})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "out_of_stock"


@pytest.mark.parametrize("quantity", [0, -1, "2.5", "abc", 10_000])
def test_invalid_quantities_rejected(seeded, shopper, quantity):
    response = shopper.post("/cart/items/", {"variant_id": variant("FS-RICE-01-5").pk, "quantity": quantity})
    assert response.status_code in (400, 409)
    assert shopper.get("/cart/").json()["item_count"] == 0


def test_stock_drop_between_cart_and_checkout(seeded, shopper):
    shopper.add("FS-RICE-01-5", 3)
    variant("FS-RICE-01-5").__class__.objects.filter(sku="FS-RICE-01-5").update(stock=2)
    response = shopper.post("/checkout/", shopper.checkout_payload())
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cart_changed"
    assert variant("FS-RICE-01-5").stock == 2


def test_idempotent_checkout_returns_same_order_only_for_same_session(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    payload = shopper.checkout_payload()
    first = shopper.post("/checkout/", payload).json()
    again = shopper.post("/checkout/", payload).json()
    assert first["number"] == again["number"]
    assert Order.objects.count() == 1

    attacker = Shopper(Client())
    attacker.add("FS-TEA-01-500")
    stolen = attacker.post("/checkout/", payload).json()
    assert stolen["number"] != first["number"]
    assert stolen["token"] != first["token"]


def test_sales_disabled_blocks_checkout(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    StoreSettings.objects.filter(pk=1).update(sales_enabled=False)
    response = shopper.post("/checkout/", shopper.checkout_payload())
    assert response.status_code == 503
    assert variant("FS-RICE-01-5").stock == 25


def test_samples_not_sellable_when_disallowed(seeded, shopper, settings):
    settings.STORE_ALLOW_SAMPLE_SALES = False
    response = shopper.post("/cart/items/", {"variant_id": variant("FS-RICE-01-5").pk, "quantity": 1})
    assert response.status_code == 409


def test_sample_orders_are_flagged_test(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    order = shopper.checkout()
    assert Order.objects.get(number=order["number"]).is_test


def test_checkout_validates_address_and_phone(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    response = shopper.post("/checkout/", shopper.checkout_payload(phone="12345", address_line="", postal_code="12"))
    assert response.status_code == 400
    fields = response.json()["error"]["fields"]
    assert {"phone", "address_line", "postal_code"} <= set(fields)


def test_shipping_method_must_serve_destination(seeded, shopper):
    shopper.add("FS-RICE-01-5")
    from apps.shipping.models import Province

    payload = shopper.checkout_payload(
        method_code="tehran-courier", province_id=Province.objects.get(name="فارس").pk, city="شیراز"
    )
    response = shopper.post("/checkout/", payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "shipping_unavailable"


def test_cart_uses_available_stock_without_a_separate_limit(seeded, shopper):
    stocked = variant("FS-RICE-01-5")
    stocked.stock = 100
    stocked.save(update_fields=["stock"])
    cart = shopper.add(stocked.sku, 100)
    assert cart["lines"][0]["quantity"] == 100
    assert cart["lines"][0]["max_quantity"] == 100
    response = shopper.post("/cart/items/", {"variant_id": stocked.pk, "quantity": 1})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"
