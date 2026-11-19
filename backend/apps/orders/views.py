import secrets

from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import Address
from apps.core.api import ApiError
from apps.core.models import StoreSettings
from apps.core.text import normalize_phone, normalize_text
from apps.orders.invoice import render_invoice_pdf
from apps.orders.models import Order, OrderEvent
from apps.orders.serializers import CheckoutSerializer, QuoteSerializer, cart_payload, order_payload
from apps.orders.services import cart as cart_service
from apps.orders.services.checkout import CheckoutInput, compute_totals, place_order
from apps.payments.services import start_payment
from apps.shipping.models import Province
from apps.shipping.services import quote_shipping


class ThrottledView(APIView):
    throttle_classes = [ScopedRateThrottle]


def _cart_response(request) -> Response:
    cart = cart_service.get_cart(request)
    priced, items = cart_service.priced_cart(cart)
    return Response(cart_payload(priced, items))


class CartView(ThrottledView):
    throttle_scope = "cart"

    def get(self, request):
        return _cart_response(request)


class CartItemsView(ThrottledView):
    throttle_scope = "cart"

    def post(self, request):
        variant_id = _int(request.data.get("variant_id"), "variant_id")
        quantity = _int(request.data.get("quantity", 1), "quantity")
        cart_service.set_quantity(request, variant_id, quantity, add=True)
        return _cart_response(request)


class CartItemView(ThrottledView):
    throttle_scope = "cart"

    def patch(self, request, variant_id: int):
        quantity = _int(request.data.get("quantity"), "quantity")
        cart_service.set_quantity(request, variant_id, quantity)
        return _cart_response(request)

    def delete(self, request, variant_id: int):
        cart_service.remove_item(request, variant_id)
        return _cart_response(request)


def _int(value, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ApiError("مقدار عددی معتبر نیست.", code="invalid", fields={field: "عدد معتبر وارد کنید."}) from None


class ProvinceListView(APIView):
    def get(self, request):
        return Response(list(Province.objects.values("id", "name")))


class QuoteView(ThrottledView):
    """Shipping options and totals for the current cart and destination."""

    throttle_scope = "cart"

    def post(self, request):
        serializer = QuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = cart_service.get_cart(request)
        priced, items = cart_service.priced_cart(cart)
        options = quote_shipping(
            province_id=serializer.validated_data.get("province_id"),
            city=normalize_text(serializer.validated_data.get("city", "")),
            weight_grams=priced.weight_grams,
            merchandise_subtotal=priced.subtotal,
        )
        store = StoreSettings.load()
        return Response(
            {
                "cart": cart_payload(priced, items),
                "shipping_options": [
                    {
                        "id": o.method.pk,
                        "name": o.method.name,
                        "kind": o.method.kind,
                        "description": o.method.description,
                        "delivery_estimate": o.method.delivery_estimate,
                        "requires_address": o.method.requires_address,
                        "available": o.available,
                        "unavailable_reason": o.unavailable_reason,
                        "cost": o.cost,
                        "is_free": o.is_free,
                        "pay_on_delivery": o.pay_on_delivery,
                        "free_threshold": o.free_threshold,
                        "totals": compute_totals(priced, o, store).__dict__ if o.available else None,
                    }
                    for o in options
                ],
                "sales_enabled": store.sales_enabled,
            }
        )


class CheckoutView(ThrottledView):
    throttle_scope = "checkout"

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        order = place_order(
            cart=cart_service.get_cart(request),
            user=request.user,
            data=CheckoutInput(
                full_name=data["full_name"],
                phone=data["phone"],
                email=data.get("email", ""),
                province_id=data.get("province_id"),
                city=data.get("city", ""),
                address_line=data.get("address_line", ""),
                postal_code=data.get("postal_code", ""),
                shipping_method_id=data["shipping_method_id"],
                customer_note=data.get("customer_note", ""),
            ),
            idempotency_key=data["idempotency_key"],
            expected_total=data.get("expected_total"),
        )
        if data.get("save_address") and request.user.is_authenticated and order.address_line:
            province = Province.objects.filter(name=order.province_name).first()
            if province and not Address.objects.filter(user=request.user, address_line=order.address_line).exists():
                Address.objects.create(
                    user=request.user,
                    full_name=order.full_name,
                    phone=order.phone,
                    province=province,
                    city=order.city,
                    address_line=order.address_line,
                    postal_code=order.postal_code,
                    is_default=not Address.objects.filter(user=request.user).exists(),
                )
        return Response(
            {"number": order.number, "token": order.access_token, "grand_total": order.grand_total}, status=201
        )


def _order_queryset():
    return Order.objects.prefetch_related(
        "items", "shipments", Prefetch("events", queryset=OrderEvent.objects.order_by("created_at"))
    ).select_related("invoice")


def get_authorized_order(request, number: str) -> Order:
    """The signed-in owner, or anyone holding the order's secret access token."""
    order = _order_queryset().filter(number=number).first()
    token = request.query_params.get("t") or request.data.get("token")
    if order is not None:
        if request.user.is_authenticated and order.user_id == request.user.pk:
            return order
        if token and secrets.compare_digest(str(token), order.access_token):
            return order
    raise ApiError("سفارش پیدا نشد.", code="not_found", status_code=404)


class OrderDetailView(APIView):
    def get(self, request, number: str):
        return Response(order_payload(get_authorized_order(request, number)))


class OrderPayView(ThrottledView):
    throttle_scope = "pay"

    def post(self, request, number: str):
        order = get_authorized_order(request, number)
        provider = str(request.data.get("provider", ""))
        if order.grand_total >= 10**10:
            raise ApiError("مبلغ سفارش بیش از سقف پرداخت آنلاین است.", code="amount_too_large")
        redirect = start_payment(order, provider, request)
        return Response({"url": redirect.url, "method": redirect.method, "params": redirect.params})


class OrderInvoiceView(APIView):
    def get(self, request, number: str):
        order = get_authorized_order(request, number)
        if not hasattr(order, "invoice"):
            raise ApiError("رسید این سفارش پس از پرداخت صادر می‌شود.", code="no_invoice", status_code=404)
        pdf = render_invoice_pdf(order)
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="receipt-{order.number}.pdf"'
        response["Cache-Control"] = "private, no-store"
        return response


class TrackView(ThrottledView):
    """Public tracking needs both the order number and the phone used on the order."""

    throttle_scope = "track"

    def post(self, request):
        number = normalize_text(str(request.data.get("number", ""))).upper()
        phone = normalize_phone(str(request.data.get("phone", "")))
        order = _order_queryset().filter(number=number).first() if number and phone else None
        if order is None or order.phone != phone:
            raise ApiError("سفارشی با این مشخصات پیدا نشد.", code="not_found", status_code=404)
        return Response(order_payload(order, include_private=False))


class AccountOrdersView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            raise ApiError("برای مشاهدهٔ سفارش‌ها وارد شوید.", code="not_authenticated", status_code=401)
        orders = _order_queryset().filter(user=request.user)[:50]
        return Response(
            [
                {
                    "number": o.number,
                    "created_at": o.created_at,
                    "grand_total": o.grand_total,
                    "status_label": o.get_status_display(),
                    "fulfillment_status_label": o.get_fulfillment_status_display(),
                    "payment_status": o.payment_status,
                    "item_count": sum(i.quantity for i in o.items.all()),
                }
                for o in orders
            ]
        )


class AccountOrderDetailView(APIView):
    def get(self, request, number: str):
        if not request.user.is_authenticated:
            raise ApiError("برای مشاهدهٔ سفارش وارد شوید.", code="not_authenticated", status_code=401)
        order = get_object_or_404(_order_queryset(), number=number, user=request.user)
        return Response(order_payload(order))
