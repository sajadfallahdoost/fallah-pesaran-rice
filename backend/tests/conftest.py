import re
import uuid
from html import unescape
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client

from apps.catalog.models import Product, ProductVariant
from apps.shipping.models import Province

API = "/api/v1"


@pytest.fixture(autouse=True)
def _isolated(request, settings, tmp_path):
    settings.STORE_ENV = "test"
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.PUBLIC_BASE_URL = "http://shop.test"
    settings.STORE_ALLOW_SAMPLE_SALES = True
    uses_db = request.node.get_closest_marker("django_db") or {"db", "transactional_db"} & set(request.fixturenames)
    if uses_db:
        cache.clear()
    yield
    if uses_db:
        cache.clear()


@pytest.fixture
def seeded(db):
    call_command("seed_store", verbosity=0, stdout=open("/dev/null", "w"))  # noqa: SIM115


@pytest.fixture
def real_catalog(seeded):
    """Seeded catalog treated as real products (not samples), so orders count in reports."""
    Product.objects.update(is_sample=False)


def variant(sku: str) -> ProductVariant:
    return ProductVariant.objects.get(sku=sku)


@pytest.fixture
def shopper():
    return Shopper(Client())


class Shopper:
    """Drives the public API like the storefront does (session cookie + JSON)."""

    def __init__(self, client: Client):
        self.client = client

    def post(self, path, data=None, **extra):
        return self.client.post(API + path, data=data or {}, content_type="application/json", **extra)

    def get(self, path, **extra):
        return self.client.get(API + path, **extra)

    def add(self, sku: str, quantity: int = 1):
        response = self.post("/cart/items/", {"variant_id": variant(sku).pk, "quantity": quantity})
        assert response.status_code == 200, response.json()
        return response.json()

    def checkout_payload(self, method_code: str = "post", **overrides):
        from apps.shipping.models import ShippingMethod

        tehran = Province.objects.get(name="تهران")
        payload = {
            "full_name": "مشتری آزمون",
            "phone": "09120000001",
            "province_id": tehran.pk,
            "city": "تهران",
            "address_line": "خیابان آزمون، پلاک ۱",
            "postal_code": "1234567890",
            "shipping_method_id": ShippingMethod.objects.get(code=method_code).pk,
            "idempotency_key": uuid.uuid4().hex,
        }
        payload.update(overrides)
        return payload

    def checkout(self, **overrides):
        response = self.post("/checkout/", self.checkout_payload(**overrides))
        assert response.status_code == 201, response.json()
        return response.json()

    def order(self, number: str, token: str):
        return self.get(f"/orders/{number}/?t={token}").json()

    def start_payment(self, number: str, token: str, provider: str = "MOCK"):
        return self.post(f"/orders/{number}/pay/?t={token}", {"provider": provider})

    def gateway_decision(self, gateway: dict, decision: str) -> str:
        """Submit a decision on the simulated gateway; returns the library callback URL."""
        page = self.client.get(urlparse(gateway["url"]).path, gateway["params"])
        assert page.status_code == 200
        fields = {k: unescape(v) for k, v in re.findall(r'name="([^"]+)" value="([^"]*)"', page.content.decode())}
        fields["decision"] = decision
        response = self.client.post(urlparse(gateway["url"]).path, fields)
        assert response.status_code == 302
        return response["Location"]

    def follow_callback(self, callback_url: str):
        """Library callback -> our return view -> storefront result URL. Returns parsed final query."""
        parsed = urlparse(callback_url)
        response = self.client.get(parsed.path, parse_qs(parsed.query))
        assert response.status_code == 302, response.content[:300]
        return_url = urlparse(response["Location"])
        assert return_url.path == "/api/v1/payments/return/"
        final = self.client.get(return_url.path, parse_qs(return_url.query))
        assert final.status_code == 302
        result = urlparse(final["Location"])
        return result, {k: v[0] for k, v in parse_qs(result.query).items()}, response["Location"]

    def pay(self, number: str, token: str, decision: str = "paid"):
        started = self.start_payment(number, token)
        assert started.status_code == 200, started.json()
        callback = self.gateway_decision(started.json(), decision)
        return self.follow_callback(callback)
