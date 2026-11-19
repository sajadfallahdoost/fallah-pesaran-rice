"""Server-side delivery eligibility and cost calculation."""

from dataclasses import dataclass

from apps.shipping.models import ShippingMethod, ShippingRate


@dataclass(frozen=True)
class ShippingOption:
    method: ShippingMethod
    available: bool
    cost: int  # rial payable with the order (0 for pay-on-delivery and free shipping)
    is_free: bool
    pay_on_delivery: bool
    unavailable_reason: str = ""
    free_threshold: int | None = None


def _rate_cost(rate: ShippingRate, weight_grams: int, merchandise_subtotal: int) -> tuple[int, bool]:
    if rate.free_shipping_threshold is not None and merchandise_subtotal >= rate.free_shipping_threshold:
        return 0, True
    extra_grams = max(0, weight_grams - rate.included_weight_grams)
    extra_kg = -(-extra_grams // 1000)  # ceiling division
    return rate.base_cost + extra_kg * rate.per_extra_kg_cost, False


def _matching_rate(method: ShippingMethod, province_id: int, city: str) -> ShippingRate | None:
    best: ShippingRate | None = None
    for rate in method.rates.all():
        zone = rate.zone
        province_ids = {p.id for p in zone.provinces.all()}
        if not zone.matches(province_id, city, province_ids):
            continue
        # A zone narrowed to cities is more specific than a whole-province zone.
        if best is None or (zone.city_list() and not best.zone.city_list()):
            best = rate
    return best


def quote_shipping(*, province_id: int | None, city: str, weight_grams: int, merchandise_subtotal: int):
    methods = ShippingMethod.objects.filter(is_active=True).prefetch_related("rates__zone__provinces")
    options: list[ShippingOption] = []
    for method in methods:
        on_delivery = method.payment_timing == ShippingMethod.PaymentTiming.ON_DELIVERY

        if weight_grams < method.min_weight_grams:
            options.append(_unavailable(method, "این روش فقط برای سفارش‌های سنگین‌تر فعال است.", on_delivery))
            continue
        if method.max_weight_grams is not None and weight_grams > method.max_weight_grams:
            options.append(_unavailable(method, "وزن سفارش از سقف این روش بیشتر است.", on_delivery))
            continue

        if method.kind == ShippingMethod.Kind.PICKUP:
            options.append(ShippingOption(method, True, 0, True, False))
            continue

        if province_id is None:
            options.append(_unavailable(method, "برای محاسبه، استان و شهر را انتخاب کنید.", on_delivery))
            continue

        rate = _matching_rate(method, province_id, city)
        if rate is None:
            options.append(_unavailable(method, "این روش برای مقصد انتخابی در دسترس نیست.", on_delivery))
            continue

        if on_delivery:
            options.append(ShippingOption(method, True, 0, False, True))
            continue

        cost, is_free = _rate_cost(rate, weight_grams, merchandise_subtotal)
        options.append(ShippingOption(method, True, cost, is_free, False, free_threshold=rate.free_shipping_threshold))
    return options


def _unavailable(method: ShippingMethod, reason: str, on_delivery: bool) -> ShippingOption:
    return ShippingOption(method, False, 0, False, on_delivery, unavailable_reason=reason)
