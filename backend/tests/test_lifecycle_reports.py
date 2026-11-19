import csv
import io

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client

from apps.catalog.models import Category, Product, ProductVariant
from apps.core.api import ApiError
from apps.core.dates import tehran_today
from apps.core.models import AuditLog
from apps.core.roles import OWNER
from apps.orders.models import Order, Refund
from apps.orders.services import lifecycle
from apps.reports import services as reports
from tests.conftest import Shopper, variant

pytestmark = pytest.mark.django_db


def _paid(shopper: Shopper, sku="FS-RICE-01-10", qty=1, real=True) -> Order:
    """Paid through the mock gateway; `real` relabels it as a live sale (mock payments are always test data)."""
    shopper.add(sku, qty)
    order = shopper.checkout()
    shopper.pay(order["number"], order["token"], "paid")
    if real:
        Order.objects.filter(number=order["number"]).update(is_test=False)
    return Order.objects.get(number=order["number"])


@pytest.fixture
def owner():
    user = get_user_model().objects.create_user(username="owner", password="x-strong-pass-1", is_staff=True)
    user.groups.add(Group.objects.get(name=OWNER))
    return user


def test_fulfillment_flow_and_invalid_jumps(real_catalog, shopper, owner):
    order = _paid(shopper)
    with pytest.raises(ApiError):
        lifecycle.advance_fulfillment(order.pk, Order.FulfillmentStatus.DELIVERED, actor=owner)
    lifecycle.advance_fulfillment(order.pk, Order.FulfillmentStatus.PREPARING, actor=owner)
    lifecycle.advance_fulfillment(order.pk, Order.FulfillmentStatus.SHIPPED, actor=owner, tracking_code="123456")
    lifecycle.advance_fulfillment(order.pk, Order.FulfillmentStatus.DELIVERED, actor=owner)
    order.refresh_from_db()
    assert order.fulfillment_status == Order.FulfillmentStatus.DELIVERED
    messages = [e["message"] for e in shopper.order(order.number, order.access_token)["events"]]
    assert any("123456" in m for m in messages)
    with pytest.raises(ApiError):
        lifecycle.cancel_order(order.pk, "دیر شد", actor=owner)


def test_unpaid_order_cannot_be_shipped(real_catalog, shopper, owner):
    shopper.add("FS-RICE-01-5")
    order = Order.objects.get(number=shopper.checkout()["number"])
    with pytest.raises(ApiError):
        lifecycle.advance_fulfillment(order.pk, Order.FulfillmentStatus.PREPARING, actor=owner)


def test_refunds_partial_full_and_restock(real_catalog, shopper, owner):
    order = _paid(shopper, qty=2)
    stock_after_sale = variant("FS-RICE-01-10").stock
    with pytest.raises(ApiError):
        lifecycle.request_refund(order.pk, order.grand_total + 10, "بیش از مبلغ", False, owner)
    with pytest.raises(ApiError):
        lifecycle.request_refund(order.pk, 1_000_000, "نیمه با بازگشت کالا", True, owner)

    partial = lifecycle.request_refund(order.pk, 1_000_000, "آسیب بسته", False, owner)
    lifecycle.set_refund_status(partial.pk, Refund.Status.APPROVED, owner)
    with pytest.raises(ApiError):
        lifecycle.set_refund_status(partial.pk, Refund.Status.COMPLETED, owner)  # needs bank reference
    lifecycle.set_refund_status(partial.pk, Refund.Status.COMPLETED, owner, external_reference="REF-1")
    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.PARTIALLY_REFUNDED
    assert lifecycle.refundable_amount(order) == order.grand_total - 1_000_000
    assert variant("FS-RICE-01-10").stock == stock_after_sale
    assert AuditLog.objects.filter(action="refund_status", object_id=str(order.pk)).count() == 2


def test_full_refund_with_restock_returns_stock(real_catalog, shopper, owner):
    order = _paid(shopper, qty=2)
    stock_after_sale = variant("FS-RICE-01-10").stock
    lifecycle.cancel_order(order.pk, "مشتری منصرف شد", actor=owner)
    order.refresh_from_db()
    assert order.needs_review  # paid + canceled must be refunded
    assert variant("FS-RICE-01-10").stock == stock_after_sale + 2  # cancel before shipping releases stock

    refund = lifecycle.request_refund(order.pk, order.grand_total, "لغو", False, owner)
    lifecycle.set_refund_status(refund.pk, Refund.Status.APPROVED, owner)
    lifecycle.set_refund_status(refund.pk, Refund.Status.COMPLETED, owner, external_reference="REF-2")
    order.refresh_from_db()
    assert order.payment_status == Order.PaymentStatus.REFUNDED
    assert variant("FS-RICE-01-10").stock == stock_after_sale + 2  # never restocked twice


def test_report_totals_match_orders_and_exclude_tests(real_catalog, shopper, owner):
    first = _paid(shopper, "FS-RICE-01-10", 1)  # 3,290,000 toman after sale price, free post
    second = _paid(shopper, "FS-TEA-01-500", 1)
    test_order = _paid(shopper, "FS-OIL-01-500", 1, real=False)
    assert test_order.is_test

    refund = lifecycle.request_refund(second.pk, 500_000, "جبران", False, owner)
    lifecycle.set_refund_status(refund.pk, Refund.Status.APPROVED, owner)
    lifecycle.set_refund_status(refund.pk, Refund.Status.COMPLETED, owner, external_reference="R")

    today = tehran_today()
    s = reports.summary(today, today)
    assert s.paid_orders == 2
    assert s.gross_merchandise == first.merchandise_total + second.merchandise_total
    assert s.discounts == first.discount_total + second.discount_total == 1_100_000
    assert s.shipping == first.shipping_total + second.shipping_total
    assert s.customer_payments == first.grand_total + second.grand_total
    assert s.refunds == 500_000
    assert s.net_sales == s.gross_merchandise - s.discounts - 500_000
    assert reports.summary(today, today, include_test=True).paid_orders == 3

    top = {row["sku"]: row for row in reports.top_products(today, today)}
    assert set(top) == {"FS-RICE-01-10", "FS-TEA-01-500"}
    cats = {row["category"]: row["revenue"] for row in reports.category_sales(today, today)}
    assert cats == {"برنج": first.items.get().line_total, "چای": second.items.get().line_total}


def test_csv_export_is_utf8_bom_and_matches(real_catalog, shopper, owner):
    order = _paid(shopper)
    client = Client()
    client.force_login(owner)
    response = client.get("/admin/reports/export/orders.csv?preset=today")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert body.startswith("\ufeff")
    rows = list(csv.reader(io.StringIO(body.lstrip("\ufeff"))))
    assert rows[1][0] == order.number
    assert rows[1][8] == str(order.grand_total)
    assert client.get("/admin/reports/export/secrets.csv").status_code == 404
    page = client.get("/admin/reports/?preset=today")
    assert page.status_code == 200
    assert "۳٬۲۹۰٬۰۰۰ تومان" in page.content.decode()


def test_seed_is_idempotent_and_preserves_owner_edits(seeded):
    Category.objects.filter(slug="rice").update(name="برنج ایرانی")
    ProductVariant.objects.filter(sku="FS-RICE-01-5").update(stock=3)
    counts = (Product.objects.count(), ProductVariant.objects.count(), Category.objects.count())
    call_command("seed_store", stdout=io.StringIO())
    assert (Product.objects.count(), ProductVariant.objects.count(), Category.objects.count()) == counts
    assert Category.objects.get(slug="rice").name == "برنج ایرانی"
    assert variant("FS-RICE-01-5").stock == 3


def test_seed_refuses_samples_in_production(db, settings):
    settings.IS_PRODUCTION = True
    with pytest.raises(Exception, match="no-samples"):
        call_command("seed_store", stdout=io.StringIO())
