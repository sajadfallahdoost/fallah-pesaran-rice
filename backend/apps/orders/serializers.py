from rest_framework import serializers

from apps.catalog.serializers import stock_status
from apps.orders.models import Order
from apps.orders.services.pricing import PricedCart
from apps.payments.models import PaymentAttempt


def cart_payload(priced: PricedCart, items) -> dict:
    by_variant = {item.variant_id: item for item in items}
    lines = []
    for line in priced.lines:
        variant = line.variant
        product = variant.product
        images = list(product.images.all())
        item = by_variant.get(variant.pk)
        lines.append(
            {
                "variant_id": variant.pk,
                "product_name": product.name,
                "product_slug": product.slug,
                "variant_title": variant.title,
                "sku": variant.sku,
                "image": {"url": images[0].image.url, "alt": images[0].alt_text} if images else None,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "list_unit_price": line.list_unit_price,
                "line_total": line.line_total,
                "stock_status": stock_status(variant),
                "max_quantity": max(0, variant.stock),
                "issue": line.issue,
                "issue_code": line.issue_code,
                "price_changed_from": (
                    item.seen_unit_price if item and item.seen_unit_price != line.unit_price else None
                ),
                "is_sample": product.is_sample,
            }
        )
    return {
        "lines": lines,
        "item_count": sum(line.quantity for line in priced.lines),
        "merchandise_total": priced.merchandise_total,
        "discount_total": priced.discount_total,
        "subtotal": priced.subtotal,
        "weight_grams": priced.weight_grams,
        "has_issues": priced.has_issues,
    }


class CheckoutSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    province_id = serializers.IntegerField(required=False, allow_null=True)
    city = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    address_line = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    customer_note = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    shipping_method_id = serializers.IntegerField()
    idempotency_key = serializers.RegexField(r"^[A-Za-z0-9\-]{16,64}$")
    expected_total = serializers.IntegerField(required=False, allow_null=True)
    save_address = serializers.BooleanField(required=False, default=False)


class QuoteSerializer(serializers.Serializer):
    province_id = serializers.IntegerField(required=False, allow_null=True)
    city = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")


def _items(order: Order) -> list[dict]:
    return [
        {
            "product_name": i.product_name,
            "variant_title": i.variant_title,
            "sku": i.sku,
            "quantity": i.quantity,
            "unit_price": i.unit_price,
            "list_unit_price": i.list_unit_price,
            "line_total": i.line_total,
        }
        for i in order.items.all()
    ]


def _shipments(order: Order) -> list[dict]:
    return [
        {
            "status": s.status,
            "status_label": s.get_status_display(),
            "carrier": s.carrier,
            "tracking_code": s.tracking_code,
            "tracking_url": s.tracking_url,
            "shipped_at": s.shipped_at,
            "delivered_at": s.delivered_at,
        }
        for s in order.shipments.all()
    ]


def _customer_stage(order: Order) -> str:
    if order.status == Order.Status.CANCELED:
        return "canceled"
    if order.status == Order.Status.EXPIRED:
        return "expired"
    if not order.is_paid:
        return "awaiting_payment"
    if order.needs_review and order.fulfillment_status == Order.FulfillmentStatus.UNFULFILLED:
        return "under_review"
    return order.fulfillment_status


def order_payload(order: Order, include_private: bool = True) -> dict:
    data = {
        "number": order.number,
        "created_at": order.created_at,
        "stage": _customer_stage(order),
        "status": order.status,
        "status_label": order.get_status_display(),
        "payment_status": order.payment_status,
        "payment_status_label": order.get_payment_status_display(),
        "fulfillment_status": order.fulfillment_status,
        "fulfillment_status_label": order.get_fulfillment_status_display(),
        "items": _items(order),
        "shipments": _shipments(order),
        "shipping_method_name": order.shipping_method_name,
        "shipping_on_delivery": order.shipping_on_delivery,
        "shipping_estimate": order.shipping_estimate,
        "events": [
            {"created_at": e.created_at, "message": e.message} for e in order.events.all() if e.is_customer_visible
        ],
    }
    if include_private:
        latest = order.payment_attempts.order_by("-created_at").first()
        data.update(
            {
                "full_name": order.full_name,
                "phone": order.phone,
                "province_name": order.province_name,
                "city": order.city,
                "address_line": order.address_line,
                "postal_code": order.postal_code,
                "merchandise_total": order.merchandise_total,
                "discount_total": order.discount_total,
                "tax_total": order.tax_total,
                "shipping_total": order.shipping_total,
                "grand_total": order.grand_total,
                "currency": order.currency,
                "paid_at": order.paid_at,
                "reservation_expires_at": order.reservation_expires_at,
                "can_pay": order.status == Order.Status.AWAITING_PAYMENT and not order.is_paid,
                "is_test": order.is_test,
                "invoice_number": getattr(getattr(order, "invoice", None), "number", None),
                "latest_payment": (
                    {
                        "status": latest.status,
                        "status_label": latest.get_status_display(),
                        "provider": latest.provider,
                        "reference_number": latest.reference_number
                        if latest.status == PaymentAttempt.Status.SUCCEEDED
                        else "",
                        "created_at": latest.created_at,
                    }
                    if latest
                    else None
                ),
            }
        )
    return data
