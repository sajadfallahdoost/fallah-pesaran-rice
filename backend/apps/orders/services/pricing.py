"""Server-side pricing. The browser never supplies prices or totals."""

from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant
from apps.core.models import StoreSettings


@dataclass
class PricedLine:
    variant: ProductVariant
    quantity: int
    list_unit_price: int
    unit_price: int
    line_discount: int
    line_total: int
    weight_grams: int
    issue: str = ""  # Persian, empty when purchasable
    issue_code: str = ""


@dataclass
class PricedCart:
    lines: list[PricedLine] = field(default_factory=list)
    merchandise_total: int = 0
    discount_total: int = 0
    weight_grams: int = 0
    contains_sample: bool = False

    @property
    def subtotal(self) -> int:
        return self.merchandise_total - self.discount_total

    @property
    def has_issues(self) -> bool:
        return any(line.issue for line in self.lines)


def variant_purchase_issue(variant: ProductVariant, quantity: int) -> tuple[str, str]:
    product = variant.product
    if not variant.is_active or product.status != Product.Status.PUBLISHED or not product.category.is_active:
        return "unavailable", "این کالا دیگر عرضه نمی‌شود."
    if product.is_sample and not settings.STORE_ALLOW_SAMPLE_SALES:
        return "sample", "این محصول نمونهٔ نمایشی است و فعلاً فروخته نمی‌شود."
    if variant.stock <= 0:
        return "out_of_stock", "موجودی این بسته تمام شده است."
    if quantity > variant.stock:
        return "insufficient_stock", f"فقط {variant.stock} بسته موجود است."
    return "", ""


def price_lines(items: list[tuple[ProductVariant, int]], now=None) -> PricedCart:
    now = now or timezone.now()
    cart = PricedCart()
    for variant, quantity in items:
        list_price = variant.price
        unit_price = variant.current_price(now)
        code, issue = variant_purchase_issue(variant, quantity)
        line = PricedLine(
            variant=variant,
            quantity=quantity,
            list_unit_price=list_price,
            unit_price=unit_price,
            line_discount=(list_price - unit_price) * quantity,
            line_total=unit_price * quantity,
            weight_grams=variant.shipping_weight_grams * quantity,
            issue=issue,
            issue_code=code,
        )
        cart.lines.append(line)
        cart.merchandise_total += list_price * quantity
        cart.discount_total += line.line_discount
        cart.weight_grams += line.weight_grams
        cart.contains_sample = cart.contains_sample or variant.product.is_sample
    return cart


def tax_for(subtotal: int, store: StoreSettings | None = None) -> int:
    """Tax on the discounted merchandise subtotal, rounded down to a whole toman. Default rate is 0."""
    store = store or StoreSettings.load()
    if not store.tax_rate_basis_points:
        return 0
    raw = subtotal * store.tax_rate_basis_points // 10_000
    return raw - raw % 10
