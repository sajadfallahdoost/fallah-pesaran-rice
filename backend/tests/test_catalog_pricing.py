from datetime import timedelta

import pytest
from django.utils import timezone

from apps.catalog.models import Product
from apps.shipping.models import Province
from apps.shipping.services import quote_shipping
from tests.conftest import variant

pytestmark = pytest.mark.django_db


def test_unit_price_per_kg_and_liter(seeded):
    assert variant("FS-RICE-01-5").unit_price() == ("کیلوگرم", 3_500_000)
    assert variant("FS-TEA-01-500").unit_price() == ("کیلوگرم", 8_400_000)
    assert variant("FS-OIL-01-500").unit_price() == ("لیتر", 13_000_000)


def test_sale_price_window(seeded):
    v = variant("FS-RICE-01-10")
    assert v.current_price() == 32_900_000
    v.sale_starts_at = timezone.now() + timedelta(days=1)
    assert v.current_price() == 34_000_000
    v.sale_starts_at, v.sale_ends_at = None, timezone.now() - timedelta(seconds=1)
    assert v.current_price() == 34_000_000


def test_public_catalog_hides_drafts(seeded, client):
    Product.objects.filter(slug="olive-oil").update(status=Product.Status.DRAFT)
    slugs = [p["slug"] for p in client.get("/api/v1/products/").json()["results"]]
    assert "olive-oil" not in slugs
    assert client.get("/api/v1/products/olive-oil/").status_code == 404


def test_product_list_filters_and_sort(seeded, client):
    data = client.get("/api/v1/products/?sort=price_desc").json()
    prices = [p["price_from"]["price"] for p in data["results"]]
    assert prices == sorted(prices, reverse=True)
    assert client.get("/api/v1/products/?category=tea").json()["count"] == 1
    assert client.get("/api/v1/products/?q=برنج").json()["count"] == 1


def test_shipping_quote_weight_tiers_and_free_threshold(seeded):
    tehran = Province.objects.get(name="تهران")
    isfahan = Province.objects.get(name="اصفهان")
    by_code = {
        o.method.code: o
        for o in quote_shipping(
            province_id=isfahan.pk, city="اصفهان", weight_grams=5_150, merchandise_subtotal=17_500_000
        )
    }
    # post: 900,000 base incl. 2 kg + ceil(3.15) = 4 extra kg × 250,000
    assert by_code["post"].cost == 1_900_000
    assert not by_code["tehran-courier"].available  # zone limited to Tehran city
    assert not by_code["freight-cod"].available  # min weight 20 kg
    free = {
        o.method.code: o
        for o in quote_shipping(
            province_id=tehran.pk, city="تهران", weight_grams=5_150, merchandise_subtotal=50_000_000
        )
    }
    assert free["post"].cost == 0 and free["post"].is_free
    assert free["tehran-courier"].available and free["tehran-courier"].cost == 1_200_000


def test_categories_follow_owner_sort_order(seeded, client):
    assert [c["slug"] for c in client.get("/api/v1/categories/").json()] == ["rice", "tea", "olive-oil"]
    assert [c["slug"] for c in client.get("/api/v1/home/").json()["categories"]] == ["rice", "tea", "olive-oil"]
