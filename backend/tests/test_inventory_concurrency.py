"""Real concurrent transactions on PostgreSQL: the last unit can only be sold once."""

import threading
import uuid

import pytest
from django.db import close_old_connections, connection

from apps.catalog.models import ProductVariant
from apps.core.api import ApiError
from apps.orders.models import Cart, CartItem, Order
from apps.orders.services.checkout import CheckoutInput, place_order
from apps.orders.services.lifecycle import cancel_order
from apps.shipping.models import Province, ShippingMethod

pytestmark = pytest.mark.django_db(transaction=True)


def _cart_with(variant: ProductVariant, quantity: int) -> Cart:
    cart = Cart.objects.create()
    CartItem.objects.create(cart=cart, variant=variant, quantity=quantity, seen_unit_price=variant.current_price())
    return cart


def _input() -> CheckoutInput:
    return CheckoutInput(
        full_name="مشتری هم‌زمان",
        phone="09120000002",
        email="",
        province_id=Province.objects.get(name="تهران").pk,
        city="تهران",
        address_line="نشانی آزمون",
        postal_code="",
        shipping_method_id=ShippingMethod.objects.get(code="post").pk,
    )


def _race(carts: list[Cart]) -> tuple[list[Order], list[Exception]]:
    barrier = threading.Barrier(len(carts))
    orders, errors = [], []
    data = _input()

    def worker(cart):
        close_old_connections()
        try:
            barrier.wait()
            orders.append(
                place_order(cart=cart, user=None, data=data, idempotency_key=uuid.uuid4().hex, expected_total=None)
            )
        except Exception as exc:  # noqa: BLE001 - collected for assertions
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(cart,)) for cart in carts]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return orders, errors


def test_last_unit_sold_once(seeded):
    v = ProductVariant.objects.get(sku="FS-TEA-01-1000")
    ProductVariant.objects.filter(pk=v.pk).update(stock=1)
    carts = [_cart_with(v, 1) for _ in range(6)]

    orders, errors = _race(carts)

    assert len(orders) == 1
    assert len(errors) == 5
    assert all(isinstance(e, ApiError) and e.error_code == "cart_changed" for e in errors)
    assert ProductVariant.objects.get(pk=v.pk).stock == 0


def test_concurrent_multi_item_orders_never_oversell(seeded):
    rice = ProductVariant.objects.get(sku="FS-RICE-01-5")
    tea = ProductVariant.objects.get(sku="FS-TEA-01-500")
    ProductVariant.objects.filter(pk=rice.pk).update(stock=3)
    ProductVariant.objects.filter(pk=tea.pk).update(stock=3)
    carts = []
    for i in range(8):
        cart = Cart.objects.create()
        # Opposite insertion order to provoke lock-order deadlocks if locks were not sorted.
        pair = [(rice, 1), (tea, 1)] if i % 2 else [(tea, 1), (rice, 1)]
        for variant, qty in pair:
            CartItem.objects.create(cart=cart, variant=variant, quantity=qty, seen_unit_price=variant.current_price())
        carts.append(cart)

    orders, errors = _race(carts)

    assert len(orders) == 3
    assert ProductVariant.objects.get(pk=rice.pk).stock == 0
    assert ProductVariant.objects.get(pk=tea.pk).stock == 0
    assert not [e for e in errors if not isinstance(e, ApiError)]


def test_cancel_releases_reservation_once(seeded):
    v = ProductVariant.objects.get(sku="FS-RICE-01-5")
    order = place_order(
        cart=_cart_with(v, 2), user=None, data=_input(), idempotency_key=uuid.uuid4().hex, expected_total=None
    )
    assert ProductVariant.objects.get(pk=v.pk).stock == 23
    cancel_order(order.pk, "درخواست مشتری")
    assert ProductVariant.objects.get(pk=v.pk).stock == 25
    with pytest.raises(ApiError):
        cancel_order(order.pk, "دوباره")
    assert ProductVariant.objects.get(pk=v.pk).stock == 25
