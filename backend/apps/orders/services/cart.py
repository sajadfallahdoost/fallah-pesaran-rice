"""Server-side cart bound to the Django session (guest) or the user (signed in)."""

from django.db import transaction

from apps.catalog.models import ProductVariant
from apps.core.api import ApiError
from apps.orders.models import Cart, CartItem
from apps.orders.services.pricing import PricedCart, price_lines, variant_purchase_issue

SESSION_KEY = "cart_token"
MAX_QUANTITY_PER_LINE = 50


def get_cart(request, create: bool = False) -> Cart | None:
    user = request.user if request.user.is_authenticated else None
    token = request.session.get(SESSION_KEY)
    cart = None
    if user:
        cart = Cart.objects.filter(user=user).order_by("-updated_at").first()
    if cart is None and token:
        cart = Cart.objects.filter(token=token, user__isnull=True).first()
        if cart and user:
            cart.user = user
            cart.save(update_fields=["user", "updated_at"])
    if cart is None and create:
        cart = Cart.objects.create(user=user)
    if cart is not None and request.session.get(SESSION_KEY) != str(cart.token):
        request.session[SESSION_KEY] = str(cart.token)
    return cart


@transaction.atomic
def merge_guest_cart_into_user(request, guest_token: str | None) -> None:
    """After sign-in, move guest cart lines into the user's cart."""
    if not guest_token:
        return
    guest = Cart.objects.filter(token=guest_token, user__isnull=True).first()
    if guest is None:
        return
    user_cart = Cart.objects.filter(user=request.user).order_by("-updated_at").first()
    if user_cart is None:
        guest.user = request.user
        guest.save(update_fields=["user", "updated_at"])
        request.session[SESSION_KEY] = str(guest.token)
        return
    for item in guest.items.all():
        existing = user_cart.items.filter(variant=item.variant).first()
        if existing:
            existing.quantity = min(existing.quantity + item.quantity, MAX_QUANTITY_PER_LINE)
            existing.save(update_fields=["quantity"])
        else:
            item.cart = user_cart
            item.save(update_fields=["cart"])
    guest.delete()
    request.session[SESSION_KEY] = str(user_cart.token)


def _load_variant(variant_id: int) -> ProductVariant:
    variant = ProductVariant.objects.select_related("product__category").filter(pk=variant_id).first()
    if variant is None:
        raise ApiError("این بسته پیدا نشد.", code="variant_not_found", status_code=404)
    return variant


def set_quantity(request, variant_id: int, quantity: int, *, add: bool = False) -> Cart:
    if quantity < (1 if add else 0) or quantity > MAX_QUANTITY_PER_LINE:
        raise ApiError(f"تعداد باید بین ۱ و {MAX_QUANTITY_PER_LINE} باشد.", code="invalid_quantity")
    variant = _load_variant(variant_id)
    cart = get_cart(request, create=True)
    item = cart.items.filter(variant=variant).first()
    new_quantity = (item.quantity if item and add else 0) + quantity

    if new_quantity == 0:
        if item:
            item.delete()
        cart.save(update_fields=["updated_at"])
        return cart

    new_quantity = min(new_quantity, MAX_QUANTITY_PER_LINE)
    code, message = variant_purchase_issue(variant, new_quantity)
    if code:
        raise ApiError(message, code=code, status_code=409)

    unit_price = variant.current_price()
    if item:
        item.quantity = new_quantity
        item.seen_unit_price = unit_price
        item.save(update_fields=["quantity", "seen_unit_price"])
    else:
        CartItem.objects.create(cart=cart, variant=variant, quantity=new_quantity, seen_unit_price=unit_price)
    cart.save(update_fields=["updated_at"])
    return cart


def remove_item(request, variant_id: int) -> Cart | None:
    cart = get_cart(request)
    if cart:
        cart.items.filter(variant_id=variant_id).delete()
        cart.save(update_fields=["updated_at"])
    return cart


def cart_items(cart: Cart | None) -> list[CartItem]:
    if cart is None:
        return []
    return list(cart.items.select_related("variant__product__category").prefetch_related("variant__product__images"))


def priced_cart(cart: Cart | None) -> tuple[PricedCart, list[CartItem]]:
    items = cart_items(cart)
    return price_lines([(item.variant, item.quantity) for item in items]), items
