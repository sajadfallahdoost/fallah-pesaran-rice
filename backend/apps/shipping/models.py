from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.money import validate_whole_toman
from apps.core.text import normalize_text


class Province(models.Model):
    name = models.CharField("نام استان", max_length=60, unique=True)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ("sort_order", "name")

    def __str__(self) -> str:
        return self.name


class ShippingZone(TimeStampedModel):
    """A delivery region: one or more provinces, optionally narrowed to specific cities."""

    name = models.CharField("نام منطقه", max_length=80)
    provinces = models.ManyToManyField(Province, verbose_name="استان‌ها", related_name="zones")
    city_names = models.TextField(
        "محدود به شهرها",
        blank=True,
        help_text="اختیاری. هر شهر در یک خط. اگر خالی باشد همهٔ شهرهای استان‌های انتخابی را شامل می‌شود.",
    )

    class Meta:
        verbose_name = "منطقهٔ ارسال"
        verbose_name_plural = "مناطق ارسال"

    def __str__(self) -> str:
        return self.name

    def city_list(self) -> list[str]:
        return [normalize_text(line) for line in self.city_names.splitlines() if line.strip()]

    def matches(self, province_id: int, city: str, province_ids: set[int] | None = None) -> bool:
        ids = province_ids if province_ids is not None else set(self.provinces.values_list("id", flat=True))
        if province_id not in ids:
            return False
        cities = self.city_list()
        return not cities or normalize_text(city) in cities


class ShippingMethod(TimeStampedModel):
    class Kind(models.TextChoices):
        POST = "post", "پست"
        COURIER = "courier", "پیک"
        FREIGHT = "freight", "باربری"
        PICKUP = "pickup", "تحویل حضوری"

    class PaymentTiming(models.TextChoices):
        PREPAID = "prepaid", "پرداخت همراه سفارش"
        ON_DELIVERY = "on_delivery", "پرداخت هزینهٔ ارسال هنگام تحویل (پس‌کرایه)"

    name = models.CharField("نام روش", max_length=80)
    code = models.SlugField("کد", max_length=40, unique=True)
    kind = models.CharField("نوع", max_length=12, choices=Kind.choices)
    payment_timing = models.CharField(
        "زمان پرداخت هزینهٔ ارسال", max_length=12, choices=PaymentTiming.choices, default=PaymentTiming.PREPAID
    )
    description = models.CharField("توضیح برای مشتری", max_length=240, blank=True)
    delivery_estimate = models.CharField(
        "زمان تقریبی تحویل",
        max_length=120,
        blank=True,
        help_text="فقط بازه‌ای که واقعاً تعهد می‌کنید. مثال: ۲ تا ۴ روز کاری",
    )
    is_active = models.BooleanField("فعال", default=True)
    min_weight_grams = models.PositiveIntegerField("حداقل وزن سفارش (گرم)", default=0)
    max_weight_grams = models.PositiveIntegerField("حداکثر وزن سفارش (گرم)", null=True, blank=True)
    requires_address = models.BooleanField("نیازمند نشانی کامل", default=True)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "روش ارسال"
        verbose_name_plural = "روش‌های ارسال"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return self.name


class ShippingRate(models.Model):
    """Tariff of a method inside a zone.

    cost = base_cost + ceil(max(0, weight - included_weight) / 1000) * per_extra_kg_cost
    and zero when merchandise subtotal >= free_shipping_threshold.
    """

    method = models.ForeignKey(ShippingMethod, verbose_name="روش ارسال", on_delete=models.CASCADE, related_name="rates")
    zone = models.ForeignKey(ShippingZone, verbose_name="منطقه", on_delete=models.CASCADE, related_name="rates")
    base_cost = models.BigIntegerField(
        "هزینهٔ پایه (ریال)", default=0, validators=[MinValueValidator(0), validate_whole_toman]
    )
    included_weight_grams = models.PositiveIntegerField("وزن شامل هزینهٔ پایه (گرم)", default=1000)
    per_extra_kg_cost = models.BigIntegerField(
        "هزینهٔ هر کیلوگرم اضافه (ریال)", default=0, validators=[MinValueValidator(0), validate_whole_toman]
    )
    free_shipping_threshold = models.BigIntegerField(
        "آستانهٔ ارسال رایگان (ریال)",
        null=True,
        blank=True,
        validators=[MinValueValidator(0), validate_whole_toman],
        help_text="جمع کالاها از این مبلغ بیشتر باشد، ارسال رایگان است. خالی = بدون ارسال رایگان.",
    )

    class Meta:
        verbose_name = "تعرفهٔ ارسال"
        verbose_name_plural = "تعرفه‌های ارسال"
        constraints = [models.UniqueConstraint(fields=["method", "zone"], name="unique_rate_per_method_zone")]

    def __str__(self) -> str:
        return f"{self.method} / {self.zone}"
