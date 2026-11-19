import uuid

from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel
from apps.orders.models import Order


class PaymentProvider(TimeStampedModel):
    """Owner-controlled availability of a gateway. Secrets live only in environment variables."""

    code = models.CharField(
        "کد درگاه", max_length=20, unique=True, help_text="همان کد کتابخانه: ZARINPAL، ZIBAL، SEP، MELLAT، BMI یا MOCK"
    )
    display_name = models.CharField("نام نمایشی", max_length=60)
    description = models.CharField("توضیح برای مشتری", max_length=160, blank=True)
    is_enabled = models.BooleanField("فعال", default=False)
    is_default = models.BooleanField("پیش‌فرض", default=False)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "درگاه پرداخت"
        verbose_name_plural = "درگاه‌های پرداخت"
        ordering = ("sort_order", "id")
        constraints = [
            models.UniqueConstraint(fields=["is_default"], condition=Q(is_default=True), name="single_default_provider")
        ]

    def __str__(self) -> str:
        return self.display_name


class PaymentAttempt(TimeStampedModel):
    class Status(models.TextChoices):
        CREATED = "created", "ایجادشده"
        REDIRECTED = "redirected", "ارسال به درگاه"
        SUCCEEDED = "succeeded", "پرداخت تأییدشده"
        FAILED = "failed", "ناموفق"
        CANCELED = "canceled", "انصراف مشتری"
        UNKNOWN = "unknown", "نامشخص، نیازمند استعلام"
        EXPIRED = "expired", "منقضی"
        MISMATCH = "mismatch", "مغایرت مبلغ/مرجع"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order = models.ForeignKey(Order, verbose_name="سفارش", on_delete=models.PROTECT, related_name="payment_attempts")
    provider = models.CharField("درگاه", max_length=20)
    status = models.CharField("وضعیت", max_length=12, choices=Status.choices, default=Status.CREATED, db_index=True)
    amount = models.BigIntegerField("مبلغ (ریال)")
    currency = models.CharField("واحد پول", max_length=3, default="IRR")
    tracking_code = models.CharField("کد پیگیری داخلی", max_length=64, unique=True, null=True, blank=True)
    reference_number = models.CharField("شمارهٔ مرجع درگاه", max_length=255, blank=True)
    bank_record = models.OneToOneField(
        "azbankgateways.Bank", verbose_name="رکورد کتابخانه", null=True, blank=True, on_delete=models.PROTECT
    )
    provider_message = models.CharField("پیام درگاه", max_length=255, blank=True)
    is_test = models.BooleanField("آزمایشی", default=False)
    verified_at = models.DateTimeField("زمان تأیید", null=True, blank=True)
    applied_to_order = models.BooleanField(
        "اعمال‌شده روی سفارش", default=False, help_text="این پرداخت سفارش را نهایی کرده است."
    )
    callback_count = models.PositiveIntegerField("تعداد بازگشت از درگاه", default=0)

    class Meta:
        verbose_name = "تلاش پرداخت"
        verbose_name_plural = "تلاش‌های پرداخت"
        ordering = ("-created_at",)
        constraints = [
            # At most one attempt may finalize an order.
            models.UniqueConstraint(
                fields=["order"], condition=Q(applied_to_order=True), name="single_applied_payment_per_order"
            )
        ]

    def __str__(self) -> str:
        return f"{self.order.number} / {self.provider} / {self.get_status_display()}"


class MockGatewayDecision(models.Model):
    """Development only: the outcome chosen on the simulated gateway page, read during verify."""

    reference_number = models.CharField(max_length=64, unique=True)
    decision = models.CharField(max_length=12)  # "paid" | "canceled" | "failed" | "timeout"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.reference_number}: {self.decision}"
