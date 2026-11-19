import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from apps.core.roles import CATALOG_EDITOR, ORDER_OPERATOR, OWNER
from tests.conftest import Shopper

pytestmark = pytest.mark.django_db


def _staff(username: str, group: str | None = None, superuser: bool = False) -> Client:
    user = get_user_model().objects.create_user(
        username=username, password="x-strong-pass-1", is_staff=True, is_superuser=superuser
    )
    if group:
        user.groups.add(Group.objects.get(name=group))
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def paid_order(seeded):
    shopper = Shopper(Client())
    shopper.add("FS-RICE-01-10", 1)
    order = shopper.checkout()
    shopper.pay(order["number"], order["token"], "paid")
    return order


def test_every_admin_page_renders_for_superuser(paid_order):
    client = _staff("root", superuser=True)
    assert client.get(reverse("admin:index")).status_code == 200
    for model, model_admin in admin.site._registry.items():
        info = f"admin:{model._meta.app_label}_{model._meta.model_name}"
        changelist = client.get(reverse(f"{info}_changelist"))
        assert changelist.status_code == 200, info
        obj = model._default_manager.first()
        if obj is not None:
            change = client.get(reverse(f"{info}_change", args=[obj.pk]))
            assert change.status_code == 200, info
        if model_admin.has_add_permission(changelist.wsgi_request):
            assert client.get(reverse(f"{info}_add")).status_code == 200, info


def test_dashboard_shows_money_only_to_report_viewers(paid_order):
    owner = _staff("owner", OWNER).get(reverse("admin:index"))
    assert owner.status_code == 200
    assert owner.context["fs_can_view_reports"] is True
    assert "fs_today_sales" in owner.context

    operator = _staff("operator", ORDER_OPERATOR).get(reverse("admin:index"))
    assert operator.status_code == 200
    assert not operator.context["fs_can_view_reports"]
    assert "fs_today_sales" not in operator.context
    assert "پرداخت تأییدشدهٔ امروز" not in operator.content.decode()


def test_reports_are_forbidden_without_financial_permission(paid_order):
    owner = _staff("owner", OWNER)
    assert owner.get(reverse("sales-report")).status_code == 200
    for group in (ORDER_OPERATOR, CATALOG_EDITOR):
        client = _staff(f"user-{group}", group)
        assert client.get(reverse("sales-report")).status_code in (302, 403)
        assert client.get(reverse("sales-report-export", args=["orders"])).status_code in (302, 403)


def test_review_filter_lists_orders(paid_order):
    client = _staff("root", superuser=True)
    response = client.get(reverse("admin:orders_order_changelist") + "?review=1")
    assert response.status_code == 200
