"""Atomic stock reservation, commit, and release.

`ProductVariant.stock` is the quantity available for new orders. A checkout moves stock
from `stock` into the order's reservation (stock_state=reserved). Successful payment commits
the reservation. Expiry/cancellation releases it back to `stock`. All mutations lock the
variant rows (SELECT ... FOR UPDATE, ordered by id to avoid deadlocks); a CHECK constraint
keeps stock non-negative as a last line of defence.
"""

from django.db import transaction
from django.db.models import F

from apps.catalog.models import ProductVariant
from apps.core.models import audit
from apps.orders.models import Order


def lock_variants(variant_ids) -> dict[int, ProductVariant]:
    variants = (
        ProductVariant.objects.select_for_update(of=("self",))
        .select_related("product__category")
        .filter(pk__in=set(variant_ids))
        .order_by("pk")
    )
    return {v.pk: v for v in variants}


def _order_quantities(order: Order) -> dict[int, int]:
    quantities: dict[int, int] = {}
    for item in order.items.all():
        if item.variant_id:
            quantities[item.variant_id] = quantities.get(item.variant_id, 0) + item.quantity
    return quantities


@transaction.atomic
def release_reservation(order: Order, reason: str, actor=None) -> bool:
    """Return reserved (or, for cancellations/restocks, committed) stock. Idempotent."""
    if order.stock_state == Order.StockState.RELEASED:
        return False
    quantities = _order_quantities(order)
    lock_variants(quantities)
    for variant_id, qty in quantities.items():
        ProductVariant.objects.filter(pk=variant_id).update(stock=F("stock") + qty)
    order.stock_state = Order.StockState.RELEASED
    order.save(update_fields=["stock_state", "updated_at"])
    audit("stock_released", order, reason, actor=actor, quantities=quantities)
    return True


@transaction.atomic
def try_reserve_again(order: Order) -> bool:
    """For a late payment after release: take stock again if every line is still available."""
    if order.stock_state != Order.StockState.RELEASED:
        return True
    quantities = _order_quantities(order)
    variants = lock_variants(quantities)
    if len(variants) != len(quantities) or any(variants[vid].stock < qty for vid, qty in quantities.items()):
        return False
    for variant_id, qty in quantities.items():
        ProductVariant.objects.filter(pk=variant_id).update(stock=F("stock") - qty)
    order.stock_state = Order.StockState.RESERVED
    order.save(update_fields=["stock_state", "updated_at"])
    audit("stock_rereserved", order, "رزرو مجدد موجودی برای پرداخت دیرهنگام", quantities=quantities)
    return True
