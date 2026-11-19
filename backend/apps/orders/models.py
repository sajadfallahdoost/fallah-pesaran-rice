import secrets
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.catalog.models import ProductVariant
from apps.core.models import TimeStampedModel
from apps.core.money import CURRENCY, validate_whole_toman
from apps.shipping.models import ShippingMethod

_ORDER_NUMBER_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_order_number() -> str:
    """Non-sequential, unambiguous order number such as FS-7K2M9Q4D."""
    return "FS-" + "".join(secrets.choice(_ORDER_NUMBER_ALPHABET) for _ in range(8))


def generate_access_token() -> str:
    return secrets.token_urlsafe(24)


class Cart(TimeStampedModel):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="carts"
    )

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"

    def __str__(self) -> str:
        return f"Cart {self.token}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Price the customer saw when adding; used only to warn about price changes.
    seen_unit_price = models.BigIntegerField()
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "variant"], name="unique_variant_per_cart")]
        ordering = ("added_at", "id")

    def __str__(self) -> str:
        return f"{self.variant_id} × {self.quantity}"


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        AWAITING_PAYMENT = "awaiting_payment", "در انتظار پرداخت"
        CONFIRMED = "confirmed", "پرداخت‌شده و تأییدشده"
        CANCELED = "canceled", "لغوشده"
        EXPIRED = "expired", "منقضی (پرداخت نشد)"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "پرداخت‌نشده"
        PAID = "paid", "پرداخت‌شده"
        PARTIALLY_REFUNDED = "partially_refunded", "بازپرداخت جزئی"
        REFUNDED = "refunded", "بازپرداخت کامل"

    class FulfillmentStatus(models.TextChoices):
        UNFULFILLED = "unfulfilled", "در انتظار آماده‌سازی"
        PREPARING = "preparing", "در حال آماده‌سازی"
        SHIPPED = "shipped", "ارسال‌شده"
        DELIVERED = "delivered", "تحویل‌شده"
        RETURNED = "returned", "مرجوع‌شده"

    class StockState(models.TextChoices):
        RESERVED = "reserved", "رزرو موقت"
        COMMITTED = "committed", "کسر قطعی"
        RELEASED = "released", "آزادشده"

    number = models.CharField("شمارهٔ سفارش", max_length=16, unique=True, default=generate_order_number)
    access_token = models.CharField(max_length=64, default=generate_access_token, editable=False)
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="حساب مشتری",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )

    status = models.CharField("وضعیت سفارش", max_length=20, choices=Status.choices, default=Status.AWAITING_PAYMENT)
    payment_status = models.CharField(
        "وضعیت پرداخت", max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    fulfillment_status = models.CharField(
        "وضعیت ارسال", max_length=20, choices=FulfillmentStatus.choices, default=FulfillmentStatus.UNFULFILLED
    )
    stock_state = models.CharField("وضعیت موجودی", max_length=12, choices=StockState.choices)
    reservation_expires_at = models.DateTimeField("پایان رزرو موجودی")
    needs_review = models.BooleanField("نیازمند بررسی", default=False, db_index=True)
    review_reason = models.CharField("علت بررسی", max_length=255, blank=True)
    is_test = models.BooleanField(
        "سفارش آزمایشی", default=False, help_text="شامل محصول نمونه یا پرداخت آزمایشی؛ در گزارش‌های فروش حساب نمی‌شود."
    )

    # Customer and delivery snapshot
    full_name = models.CharField("نام گیرنده", max_length=100)
    phone = models.CharField("موبایل", max_length=11, db_index=True)
    email = models.EmailField("ایمیل", blank=True)
    province_name = models.CharField("استان", max_length=60, blank=True)
    city = models.CharField("شهر", max_length=60, blank=True)
    address_line = models.CharField("نشانی", max_length=300, blank=True)
    postal_code = models.CharField("کد پستی", max_length=10, blank=True)
    customer_note = models.CharField("توضیح مشتری", max_length=500, blank=True)

    shipping_method = models.ForeignKey(
        ShippingMethod, verbose_name="روش ارسال", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    shipping_method_name = models.CharField("روش ارسال (ثبت‌شده)", max_length=80)
    shipping_payment_timing = models.CharField("زمان پرداخت ارسال", max_length=12)
    shipping_estimate = models.CharField("زمان تقریبی تحویل", max_length=120, blank=True)
    total_weight_grams = models.PositiveIntegerField("وزن کل (گرم)", default=0)

    # Money snapshot (IRR)
    currency = models.CharField("واحد پول", max_length=3, default=CURRENCY, editable=False)
    merchandise_total = models.BigIntegerField("جمع کالاها با قیمت اصلی", default=0)
    discount_total = models.BigIntegerField("تخفیف", default=0)
    tax_total = models.BigIntegerField("مالیات", default=0)
    shipping_total = models.BigIntegerField("هزینهٔ ارسال دریافتی", default=0)
    grand_total = models.BigIntegerField("مبلغ قابل پرداخت", default=0)

    paid_at = models.DateTimeField("زمان پرداخت", null=True, blank=True, db_index=True)
    canceled_at = models.DateTimeField("زمان لغو", null=True, blank=True)
    cancel_reason = models.CharField("علت لغو", max_length=255, blank=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "reservation_expires_at"]),
            models.Index(fields=["payment_status", "paid_at"]),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(grand_total__gte=0), name="order_total_non_negative"),
        ]
        permissions = [
            ("process_fulfillment", "Can process order fulfillment"),
            ("manage_refunds", "Can record cancellations and refunds"),
            ("view_financial_reports", "Can view financial reports"),
        ]

    def __str__(self) -> str:
        return self.number

    @property
    def subtotal(self) -> int:
        return self.merchandise_total - self.discount_total

    @property
    def is_paid(self) -> bool:
        return self.payment_status != self.PaymentStatus.UNPAID

    @property
    def shipping_on_delivery(self) -> bool:
        return self.shipping_payment_timing == ShippingMethod.PaymentTiming.ON_DELIVERY


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(ProductVariant, null=True, on_delete=models.SET_NULL, related_name="+")
    product_name = models.CharField("محصول", max_length=140)
    variant_title = models.CharField("بسته", max_length=80)
    sku = models.CharField("کد کالا", max_length=40)
    package_amount = models.DecimalField("مقدار بسته", max_digits=8, decimal_places=3)
    package_unit = models.CharField("واحد", max_length=8)
    list_unit_price = models.BigIntegerField("قیمت اصلی واحد")
    unit_price = models.BigIntegerField("قیمت پرداختی واحد")
    quantity = models.PositiveIntegerField("تعداد", validators=[MinValueValidator(1)])
    line_discount = models.BigIntegerField("تخفیف ردیف", default=0)
    line_total = models.BigIntegerField("جمع ردیف")
    unit_weight_grams = models.PositiveIntegerField("وزن واحد (گرم)")
    is_sample_product = models.BooleanField(default=False)

    class Meta:
        verbose_name = "قلم سفارش"
        verbose_name_plural = "اقلام سفارش"
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.product_name} — {self.variant_title} × {self.quantity}"


class OrderEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    created_at = models.DateTimeField("زمان", auto_now_add=True)
    kind = models.CharField("نوع", max_length=40)
    message = models.CharField("شرح", max_length=300)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    is_customer_visible = models.BooleanField("قابل مشاهده برای مشتری", default=False)

    class Meta:
        verbose_name = "رویداد سفارش"
        verbose_name_plural = "تاریخچهٔ سفارش"
        ordering = ("created_at", "id")

    def __str__(self) -> str:
        return self.message


class Shipment(TimeStampedModel):
    class Status(models.TextChoices):
        PREPARING = "preparing", "در حال آماده‌سازی"
        SHIPPED = "shipped", "ارسال‌شده"
        DELIVERED = "delivered", "تحویل‌شده"
        RETURNED = "returned", "برگشتی"

    order = models.ForeignKey(Order, verbose_name="سفارش", on_delete=models.CASCADE, related_name="shipments")
    status = models.CharField("وضعیت", max_length=12, choices=Status.choices, default=Status.PREPARING)
    carrier = models.CharField("شرکت/روش حمل", max_length=80, blank=True)
    tracking_code = models.CharField("کد رهگیری مرسوله", max_length=64, blank=True)
    tracking_url = models.URLField("پیوند رهگیری", blank=True)
    shipped_at = models.DateTimeField("زمان ارسال", null=True, blank=True)
    delivered_at = models.DateTimeField("زمان تحویل", null=True, blank=True)
    note = models.CharField("یادداشت داخلی", max_length=255, blank=True)

    class Meta:
        verbose_name = "مرسوله"
        verbose_name_plural = "مرسوله‌ها"
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"{self.order.number} — {self.get_status_display()}"


class Invoice(models.Model):
    """Order receipt. Not an official tax invoice (سامانهٔ مؤدیان) unless integrated later."""

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="invoice")
    number = models.CharField("شمارهٔ رسید", max_length=24, unique=True)
    issued_at = models.DateTimeField("تاریخ صدور", auto_now_add=True)

    class Meta:
        verbose_name = "رسید فروش"
        verbose_name_plural = "رسیدهای فروش"
        ordering = ("-issued_at",)

    def __str__(self) -> str:
        return self.number


class Refund(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "ثبت درخواست"
        APPROVED = "approved", "تأییدشده، در انتظار واریز"
        COMPLETED = "completed", "واریزشده (با مرجع)"
        REJECTED = "rejected", "ردشده"

    order = models.ForeignKey(Order, verbose_name="سفارش", on_delete=models.PROTECT, related_name="refunds")
    amount = models.BigIntegerField("مبلغ (ریال)", validators=[MinValueValidator(10), validate_whole_toman])
    reason = models.CharField("علت", max_length=255)
    status = models.CharField("وضعیت", max_length=12, choices=Status.choices, default=Status.REQUESTED)
    restock = models.BooleanField(
        "بازگشت کالا به موجودی", default=False, help_text="فقط وقتی کالا سالم به انبار برگشته است."
    )
    method = models.CharField("روش بازپرداخت", max_length=60, default="واریز دستی")
    external_reference = models.CharField(
        "مرجع واریز", max_length=80, blank=True, help_text="شمارهٔ پیگیری بانکی واریز. برای وضعیت «واریزشده» الزامی است."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="ثبت‌کننده", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    completed_at = models.DateTimeField("زمان واریز", null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "بازپرداخت"
        verbose_name_plural = "بازپرداخت‌ها"
        ordering = ("-created_at",)
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="refund_amount_positive")]

    def __str__(self) -> str:
        return f"{self.order.number} — {self.amount}"
