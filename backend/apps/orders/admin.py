from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from apps.core.admin_fields import TomanField, toman
from apps.core.api import ApiError
from apps.core.dates import to_jalali_str
from apps.core.models import audit
from apps.orders.invoice import render_invoice_pdf
from apps.orders.models import Invoice, Order, OrderEvent, OrderItem, Refund, Shipment
from apps.orders.services import lifecycle
from apps.payments.models import PaymentAttempt


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ItemInline(ReadOnlyInline):
    model = OrderItem
    fields = (
        "product_name",
        "variant_title",
        "sku",
        "quantity",
        "unit_price_display",
        "discount_display",
        "line_total_display",
    )
    readonly_fields = fields

    @admin.display(description="قیمت واحد")
    def unit_price_display(self, obj):
        return toman(obj.unit_price)

    @admin.display(description="تخفیف")
    def discount_display(self, obj):
        return toman(obj.line_discount)

    @admin.display(description="جمع")
    def line_total_display(self, obj):
        return toman(obj.line_total)


class ShipmentInline(ReadOnlyInline):
    model = Shipment
    fields = ("status", "carrier", "tracking_code", "shipped", "delivered", "note")
    readonly_fields = fields

    @admin.display(description="ارسال")
    def shipped(self, obj):
        return to_jalali_str(obj.shipped_at)

    @admin.display(description="تحویل")
    def delivered(self, obj):
        return to_jalali_str(obj.delivered_at)


class PaymentInline(ReadOnlyInline):
    model = PaymentAttempt
    fields = ("created", "provider", "status", "amount_display", "reference_number", "applied_to_order", "is_test")
    readonly_fields = fields

    @admin.display(description="زمان")
    def created(self, obj):
        return to_jalali_str(obj.created_at)

    @admin.display(description="مبلغ")
    def amount_display(self, obj):
        return toman(obj.amount)


class RefundInline(ReadOnlyInline):
    model = Refund
    fields = ("created", "amount_display", "reason", "status", "restock", "external_reference", "created_by")
    readonly_fields = fields

    @admin.display(description="زمان")
    def created(self, obj):
        return to_jalali_str(obj.created_at)

    @admin.display(description="مبلغ")
    def amount_display(self, obj):
        return toman(obj.amount)


class EventInline(ReadOnlyInline):
    model = OrderEvent
    fields = ("when", "message", "actor", "is_customer_visible")
    readonly_fields = fields

    @admin.display(description="زمان")
    def when(self, obj):
        return to_jalali_str(obj.created_at)


class NeedsReviewFilter(admin.SimpleListFilter):
    title = "نیازمند بررسی"
    parameter_name = "review"

    def lookups(self, request, model_admin):
        return (("1", "بله"),)

    def queryset(self, request, queryset):
        return queryset.filter(needs_review=True) if self.value() == "1" else queryset


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_form_template = "admin/orders/order/change_form.html"
    inlines = (ItemInline, PaymentInline, ShipmentInline, RefundInline, EventInline)
    list_display = (
        "number",
        "created",
        "full_name",
        "phone",
        "total",
        "status",
        "payment_status",
        "fulfillment_status",
        "flags",
    )
    list_filter = (
        NeedsReviewFilter,
        "status",
        "payment_status",
        "fulfillment_status",
        "is_test",
        "shipping_method_name",
    )
    search_fields = ("number", "phone", "full_name", "payment_attempts__reference_number")
    date_hierarchy = "created_at"
    list_per_page = 30
    readonly_fields = (
        "number",
        "created",
        "user",
        "status",
        "payment_status",
        "fulfillment_status",
        "stock_state",
        "reservation_expires",
        "needs_review",
        "review_reason",
        "is_test",
        "full_name",
        "phone",
        "email",
        "province_name",
        "city",
        "address_line",
        "postal_code",
        "customer_note",
        "shipping_method_name",
        "shipping_payment_timing",
        "shipping_estimate",
        "total_weight_grams",
        "money_merchandise",
        "money_discount",
        "money_tax",
        "money_shipping",
        "money_total",
        "paid",
        "canceled_at",
        "cancel_reason",
    )
    fieldsets = (
        (
            "سفارش",
            {
                "fields": (
                    "number",
                    "created",
                    "user",
                    "is_test",
                    "status",
                    "payment_status",
                    "fulfillment_status",
                    "stock_state",
                    "reservation_expires",
                    "paid",
                )
            },
        ),
        ("بررسی", {"fields": ("needs_review", "review_reason", "canceled_at", "cancel_reason")}),
        (
            "گیرنده",
            {
                "fields": (
                    "full_name",
                    "phone",
                    "email",
                    "province_name",
                    "city",
                    "address_line",
                    "postal_code",
                    "customer_note",
                )
            },
        ),
        (
            "ارسال",
            {"fields": ("shipping_method_name", "shipping_payment_timing", "shipping_estimate", "total_weight_grams")},
        ),
        ("مبالغ", {"fields": ("money_merchandise", "money_discount", "money_tax", "money_shipping", "money_total")}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")

    @admin.display(description="ثبت", ordering="created_at")
    def created(self, obj):
        return to_jalali_str(obj.created_at)

    @admin.display(description="پرداخت", ordering="paid_at")
    def paid(self, obj):
        return to_jalali_str(obj.paid_at)

    @admin.display(description="پایان رزرو")
    def reservation_expires(self, obj):
        return to_jalali_str(obj.reservation_expires_at)

    @admin.display(description="مبلغ", ordering="grand_total")
    def total(self, obj):
        return toman(obj.grand_total)

    @admin.display(description="نشان‌ها")
    def flags(self, obj):
        parts = []
        if obj.needs_review:
            parts.append('<span class="fs-badge fs-badge-alert">بررسی</span>')
        if obj.is_test:
            parts.append('<span class="fs-badge">آزمایشی</span>')
        return format_html("".join(parts)) if parts else "—"

    @admin.display(description="جمع کالا (قیمت اصلی)")
    def money_merchandise(self, obj):
        return toman(obj.merchandise_total)

    @admin.display(description="تخفیف")
    def money_discount(self, obj):
        return toman(obj.discount_total)

    @admin.display(description="مالیات")
    def money_tax(self, obj):
        return toman(obj.tax_total)

    @admin.display(description="هزینهٔ ارسال دریافتی")
    def money_shipping(self, obj):
        return toman(obj.shipping_total)

    @admin.display(description="مبلغ قابل پرداخت")
    def money_total(self, obj):
        return toman(obj.grand_total)

    # --- operations ---------------------------------------------------------------

    def get_urls(self):
        return [
            path(
                "<int:pk>/operate/<str:operation>/",
                self.admin_site.admin_view(self.operate),
                name="orders_order_operate",
            ),
            path("<int:pk>/receipt.pdf", self.admin_site.admin_view(self.receipt), name="orders_order_receipt"),
        ] + super().get_urls()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        order = get_object_or_404(Order, pk=object_id)
        extra = {
            "fs_order": order,
            "fs_can_fulfill": request.user.has_perm("orders.process_fulfillment"),
            "fs_can_refund": request.user.has_perm("orders.manage_refunds"),
            "fs_next_steps": lifecycle._FULFILLMENT_FLOW.get(order.fulfillment_status, set()),
            "fs_refundable": toman(lifecycle.refundable_amount(order)) if order.is_paid else None,
            "fs_refunds": order.refunds.all(),
            "fs_has_invoice": Invoice.objects.filter(order=order).exists(),
            "fs_unresolved_payments": order.payment_attempts.filter(
                status__in=[PaymentAttempt.Status.UNKNOWN, PaymentAttempt.Status.REDIRECTED]
            ).exists(),
        }
        extra.update(extra_context or {})
        return super().change_view(request, object_id, form_url, extra)

    def receipt(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if not request.user.has_perm("orders.view_order") or not hasattr(order, "invoice"):
            raise PermissionDenied
        response = HttpResponse(render_invoice_pdf(order), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="receipt-{order.number}.pdf"'
        response["Cache-Control"] = "private, no-store"
        return response

    def operate(self, request, pk, operation):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        return _operate(self, request, pk, operation)


def _operate(model_admin, request, pk, operation):
    order = get_object_or_404(Order, pk=pk)
    back = HttpResponseRedirect(reverse("admin:orders_order_change", args=[pk]))
    user = request.user
    data = request.POST
    fulfillment = {"preparing", "shipped", "delivered", "returned"}
    try:
        if operation in fulfillment:
            if not user.has_perm("orders.process_fulfillment"):
                raise PermissionDenied
            lifecycle.advance_fulfillment(
                order.pk,
                operation,
                actor=user,
                carrier=data.get("carrier", "").strip(),
                tracking_code=data.get("tracking_code", "").strip(),
                tracking_url=data.get("tracking_url", "").strip(),
                note=data.get("note", "").strip(),
            )
        elif operation == "cancel":
            if not user.has_perm("orders.manage_refunds"):
                raise PermissionDenied
            lifecycle.cancel_order(order.pk, data.get("reason", ""), actor=user)
        elif operation == "refund":
            if not user.has_perm("orders.manage_refunds"):
                raise PermissionDenied
            amount_field = TomanField(required=True)
            amount = amount_field.clean(data.get("amount", ""))
            lifecycle.request_refund(order.pk, amount, data.get("reason", ""), data.get("restock") == "on", user)
        elif operation in {"refund_approved", "refund_completed", "refund_rejected"}:
            if not user.has_perm("orders.manage_refunds"):
                raise PermissionDenied
            refund = get_object_or_404(Refund, pk=data.get("refund_id"), order=order)
            lifecycle.set_refund_status(
                refund.pk,
                operation.removeprefix("refund_"),
                user,
                external_reference=data.get("external_reference", ""),
            )
        elif operation == "recheck_payment":
            from apps.payments.services import reconcile_attempt

            if not user.has_perm("orders.view_order"):
                raise PermissionDenied
            for attempt in order.payment_attempts.filter(
                status__in=[PaymentAttempt.Status.UNKNOWN, PaymentAttempt.Status.REDIRECTED]
            ):
                reconcile_attempt(attempt)
        elif operation == "resolve_review":
            if not user.has_perm("orders.manage_refunds"):
                raise PermissionDenied
            note = data.get("note", "").strip()
            if not note:
                raise ApiError("شرح اقدام انجام‌شده را بنویسید.")
            Order.objects.filter(pk=order.pk).update(needs_review=False)
            OrderEvent.objects.create(order=order, kind="review_resolved", message=f"بررسی بسته شد: {note}", actor=user)
            audit("review_resolved", order, note, actor=user)
        else:
            raise PermissionDenied
    except ApiError as exc:
        model_admin.message_user(request, str(exc.detail), messages.ERROR)
        return back
    except ValidationError as exc:
        model_admin.message_user(request, " ".join(exc.messages), messages.ERROR)
        return back
    model_admin.message_user(request, "انجام شد.", messages.SUCCESS)
    return back


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("order", "created", "amount_display", "status", "external_reference", "created_by")
    list_filter = ("status",)
    search_fields = ("order__number", "external_reference")
    readonly_fields = [f.name for f in Refund._meta.fields]

    @admin.display(description="زمان", ordering="created_at")
    def created(self, obj):
        return to_jalali_str(obj.created_at)

    @admin.display(description="مبلغ", ordering="amount")
    def amount_display(self, obj):
        return toman(obj.amount)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "issued", "pdf")
    search_fields = ("number", "order__number")
    readonly_fields = ("number", "order", "issued_at")

    @admin.display(description="تاریخ صدور", ordering="issued_at")
    def issued(self, obj):
        return to_jalali_str(obj.issued_at)

    @admin.display(description="PDF")
    def pdf(self, obj):
        return format_html(
            '<a href="{}" target="_blank">دریافت</a>', reverse("admin:orders_order_receipt", args=[obj.order_id])
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
