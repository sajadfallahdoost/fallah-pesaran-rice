from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.validators import validate_image_upload


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        abstract = True


class StoreSettings(models.Model):
    """Singleton with owner-editable public store information."""

    store_name = models.CharField("نام فروشگاه", max_length=80, default="فلاح و پسران")
    tagline = models.CharField(
        "شعار کوتاه", max_length=160, blank=True, default="برنج ایرانی و خوراکی‌های برگزیده برای سفرهٔ خانواده"
    )
    phone = models.CharField("تلفن (لاتین)", max_length=20, default="09122122187")
    email = models.EmailField("ایمیل", default="fallahdoostsajad@gmail.com")
    telegram_username = models.CharField("نام کاربری تلگرام", max_length=64, default="Sajadfallahdoost")
    address = models.CharField("نشانی عمومی", max_length=255, default="تهران، میرداماد، میدان مادر")
    business_hours = models.CharField(
        "ساعات پاسخ‌گویی", max_length=160, blank=True, help_text="تا زمانی که مالک اعلام نکرده، خالی بماند."
    )
    announcement = models.CharField("پیام نوار بالای سایت", max_length=200, blank=True)
    sales_enabled = models.BooleanField(
        "پذیرش سفارش فعال است",
        default=True,
        help_text="با غیرفعال کردن، مشتری همچنان محصولات را می‌بیند اما ثبت سفارش ممکن نیست.",
    )
    tax_rate_basis_points = models.PositiveIntegerField(
        "نرخ مالیات (واحد پایه = ۰٫۰۱٪)",
        default=0,
        help_text="فقط پس از تأیید مشاور مالیاتی تنظیم شود. مثال: ۱۰۰۰ یعنی ۱۰٪. پیش‌فرض صفر است.",
    )
    seo_title = models.CharField("عنوان سئو صفحهٔ اصلی", max_length=70, blank=True)
    seo_description = models.CharField("توضیح سئو صفحهٔ اصلی", max_length=170, blank=True)

    class Meta:
        verbose_name = "تنظیمات فروشگاه"
        verbose_name_plural = "تنظیمات فروشگاه"

    def __str__(self) -> str:
        return "تنظیمات فروشگاه"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("تنظیمات فروشگاه قابل حذف نیست.")

    @classmethod
    def load(cls) -> "StoreSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class HomeBanner(TimeStampedModel):
    title = models.CharField("عنوان", max_length=120)
    subtitle = models.CharField("متن کوتاه", max_length=240, blank=True)
    eyebrow = models.CharField("برچسب بالای عنوان", max_length=60, blank=True)
    image_desktop = models.ImageField("تصویر دسکتاپ", upload_to="banners/", validators=[validate_image_upload])
    image_mobile = models.ImageField(
        "تصویر موبایل", upload_to="banners/", blank=True, validators=[validate_image_upload]
    )
    image_alt = models.CharField("متن جایگزین تصویر", max_length=200)
    cta_label = models.CharField("متن دکمه", max_length=40, blank=True)
    cta_url = models.CharField("پیوند دکمه", max_length=200, blank=True, help_text="مثال: /category/rice")
    is_active = models.BooleanField("فعال", default=True)
    is_generated_sample = models.BooleanField(
        "تصویر نمونهٔ تولیدی", default=False, help_text="تصویر ساخته‌شده با هوش مصنوعی؛ عکس واقعی محصول نیست."
    )
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "بنر صفحهٔ اصلی"
        verbose_name_plural = "بنرهای صفحهٔ اصلی"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return self.title


class Page(TimeStampedModel):
    slug = models.SlugField("نشانی", max_length=60, unique=True, allow_unicode=False)
    title = models.CharField("عنوان", max_length=120)
    summary = models.CharField("خلاصه", max_length=240, blank=True)
    body = models.TextField("متن", help_text="پاراگراف‌ها را با یک خط خالی جدا کنید. خطی که با ## شروع شود تیتر است.")
    requires_owner_review = models.BooleanField(
        "نیازمند تأیید مالک",
        default=True,
        help_text="تا وقتی فعال است، در سایت برچسب «پیش‌نویس سیاست» نمایش داده می‌شود.",
    )
    is_published = models.BooleanField("منتشرشده", default=True)
    seo_title = models.CharField("عنوان سئو", max_length=70, blank=True)
    seo_description = models.CharField("توضیح سئو", max_length=170, blank=True)

    class Meta:
        verbose_name = "صفحهٔ محتوایی"
        verbose_name_plural = "صفحه‌های محتوایی"
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title


class FAQ(TimeStampedModel):
    question = models.CharField("پرسش", max_length=200)
    answer = models.TextField("پاسخ")
    group = models.CharField("گروه", max_length=60, default="عمومی")
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "پرسش متداول"
        verbose_name_plural = "پرسش‌های متداول"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return self.question


class AuditLog(models.Model):
    """Append-only record of consequential operations (orders, payments, refunds, stock)."""

    created_at = models.DateTimeField("زمان", auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="کاربر", null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField("عملیات", max_length=60, db_index=True)
    object_type = models.CharField("نوع", max_length=60)
    object_id = models.CharField("شناسه", max_length=64, db_index=True)
    message = models.CharField("شرح", max_length=255)
    data = models.JSONField("داده", default=dict, blank=True)

    class Meta:
        verbose_name = "رویداد ممیزی"
        verbose_name_plural = "رویدادهای ممیزی"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}#{self.object_id}"


def audit(action: str, obj, message: str, actor=None, **data) -> AuditLog:
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj._meta.model_name,
        object_id=str(obj.pk),
        message=message[:255],
        data=data,
    )
