from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.shipping.models import Province


class Address(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="کاربر", on_delete=models.CASCADE, related_name="addresses"
    )
    label = models.CharField("عنوان", max_length=40, blank=True, help_text="مثال: خانه")
    full_name = models.CharField("نام گیرنده", max_length=100)
    phone = models.CharField("موبایل گیرنده", max_length=11)
    province = models.ForeignKey(Province, verbose_name="استان", on_delete=models.PROTECT)
    city = models.CharField("شهر", max_length=60)
    address_line = models.CharField("نشانی", max_length=300)
    postal_code = models.CharField("کد پستی", max_length=10, blank=True)
    is_default = models.BooleanField("پیش‌فرض", default=False)

    class Meta:
        verbose_name = "نشانی"
        verbose_name_plural = "نشانی‌ها"
        ordering = ("-is_default", "-updated_at")

    def __str__(self) -> str:
        return f"{self.full_name} — {self.city}"


class OtpCode(models.Model):
    phone = models.CharField("موبایل", max_length=11, db_index=True)
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    requester_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "کد ورود"
        verbose_name_plural = "کدهای ورود"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"OTP {self.phone[:4]}***{self.phone[-2:]}"
