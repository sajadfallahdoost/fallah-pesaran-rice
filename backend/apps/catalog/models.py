from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.core.money import validate_whole_toman
from apps.core.validators import validate_image_upload


class Category(TimeStampedModel):
    name = models.CharField("نام", max_length=80)
    slug = models.SlugField(
        "نشانی (لاتین)", max_length=80, unique=True, help_text="پس از انتشار تغییر ندهید؛ پیوندها خراب می‌شوند."
    )
    description = models.TextField("توضیح", blank=True)
    image = models.ImageField("تصویر", upload_to="categories/", blank=True, validators=[validate_image_upload])
    image_alt = models.CharField("متن جایگزین تصویر", max_length=200, blank=True)
    is_active = models.BooleanField("فعال", default=True)
    show_in_navigation = models.BooleanField("نمایش در منو", default=True)
    show_when_empty = models.BooleanField(
        "نمایش حتی بدون محصول", default=False, help_text="در این حالت پیام «به‌زودی» نمایش داده می‌شود."
    )
    sort_order = models.PositiveIntegerField("ترتیب", default=0)
    seo_title = models.CharField("عنوان سئو", max_length=70, blank=True)
    seo_description = models.CharField("توضیح سئو", max_length=170, blank=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ("sort_order", "name")

    def __str__(self) -> str:
        return self.name


class ProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Product.Status.PUBLISHED, category__is_active=True)


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        PUBLISHED = "published", "منتشرشده"
        ARCHIVED = "archived", "بایگانی"

    name = models.CharField("نام محصول", max_length=140)
    slug = models.SlugField("نشانی (لاتین)", max_length=140, unique=True)
    sku = models.CharField("کد کالا (SKU)", max_length=40, unique=True)
    category = models.ForeignKey(Category, verbose_name="دسته‌بندی", on_delete=models.PROTECT, related_name="products")
    status = models.CharField("وضعیت انتشار", max_length=12, choices=Status.choices, default=Status.DRAFT)
    is_sample = models.BooleanField(
        "محصول نمونه (نمایشی)",
        default=False,
        help_text="محصول نمایشی با قیمت و موجودی آزمایشی. در محیط تولید قابل خرید نیست.",
    )
    is_featured = models.BooleanField("نمایش در صفحهٔ اصلی", default=False)
    short_description = models.CharField("توضیح کوتاه", max_length=240)
    description = models.TextField("توضیح کامل", blank=True)
    storage_and_use = models.TextField("نگهداری و مصرف", blank=True)
    related_products = models.ManyToManyField("self", verbose_name="محصولات مرتبط", blank=True, symmetrical=True)
    seo_title = models.CharField("عنوان سئو", max_length=70, blank=True)
    seo_description = models.CharField("توضیح سئو", max_length=170, blank=True)
    published_at = models.DateTimeField("زمان انتشار", null=True, blank=True)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ("sort_order", "-published_at", "name")
        indexes = [models.Index(fields=["status", "category"])]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_storefront_path(self) -> str:
        return f"/product/{self.slug}"

    def get_absolute_url(self) -> str:
        return reverse("admin:catalog_product_change", args=[self.pk])


class ProductImage(models.Model):
    product = models.ForeignKey(Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("تصویر", upload_to="products/", validators=[validate_image_upload])
    alt_text = models.CharField("متن جایگزین", max_length=200)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)
    is_generated_sample = models.BooleanField(
        "تصویر نمونهٔ تولیدی", default=False, help_text="تصویر تزئینی ساخته‌شده؛ کالای ارسالی دقیقاً همین نیست."
    )

    class Meta:
        verbose_name = "تصویر محصول"
        verbose_name_plural = "گالری تصاویر"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return self.alt_text


class ProductAttribute(models.Model):
    """Category-specific facts (variety, origin, harvest, tea type...). Only verified facts."""

    product = models.ForeignKey(Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="attributes")
    name = models.CharField("ویژگی", max_length=60)
    value = models.CharField("مقدار", max_length=160)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "ویژگی"
        verbose_name_plural = "ویژگی‌ها"
        ordering = ("sort_order", "id")

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"


class ProductVariant(TimeStampedModel):
    """A purchasable package. Sold in whole packages only (integer quantity)."""

    class Unit(models.TextChoices):
        KILOGRAM = "kg", "کیلوگرم"
        GRAM = "g", "گرم"
        LITER = "l", "لیتر"
        MILLILITER = "ml", "میلی‌لیتر"
        PIECE = "piece", "عدد"

    product = models.ForeignKey(Product, verbose_name="محصول", on_delete=models.CASCADE, related_name="variants")
    title = models.CharField("عنوان بسته", max_length=80, help_text="مثال: کیسهٔ ۵ کیلوگرمی")
    sku = models.CharField("کد کالا (SKU)", max_length=40, unique=True)
    package_amount = models.DecimalField(
        "مقدار هر بسته", max_digits=8, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))]
    )
    package_unit = models.CharField("واحد", max_length=8, choices=Unit.choices, default=Unit.KILOGRAM)
    price = models.BigIntegerField(
        "قیمت هر بسته (ریال)",
        validators=[MinValueValidator(10), validate_whole_toman],
        help_text="به ریال وارد کنید. مثال: ۱٬۲۵۰٬۰۰۰ تومان = 12500000 ریال.",
    )
    sale_price = models.BigIntegerField(
        "قیمت فروش ویژه (ریال)", null=True, blank=True, validators=[MinValueValidator(10), validate_whole_toman]
    )
    sale_starts_at = models.DateTimeField("شروع فروش ویژه", null=True, blank=True)
    sale_ends_at = models.DateTimeField("پایان فروش ویژه", null=True, blank=True)
    stock = models.IntegerField(
        "موجودی قابل فروش",
        default=0,
        validators=[MinValueValidator(0)],
        help_text=(
            "تعداد بستهٔ آمادهٔ فروش. اگر هم‌زمان سفارشی ثبت شود، تغییر شما به‌صورت افزایش/کاهش "
            "نسبت به عدد نمایش‌داده‌شده اعمال می‌شود تا رزرو مشتری از بین نرود."
        ),
    )
    low_stock_threshold = models.PositiveIntegerField("آستانهٔ هشدار موجودی", default=5)
    shipping_weight_grams = models.PositiveIntegerField(
        "وزن ارسال هر بسته (گرم)", help_text="وزن با بسته‌بندی، برای محاسبهٔ هزینهٔ ارسال."
    )
    is_active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "بستهٔ قابل خرید"
        verbose_name_plural = "بسته‌ها و قیمت‌ها"
        ordering = ("sort_order", "package_amount")
        constraints = [
            models.CheckConstraint(condition=Q(stock__gte=0), name="variant_stock_non_negative"),
            models.CheckConstraint(condition=Q(price__gt=0), name="variant_price_positive"),
            models.CheckConstraint(
                condition=Q(sale_price__isnull=True) | Q(sale_price__lt=models.F("price")),
                name="variant_sale_below_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.title}"

    def clean(self):
        if self.sale_price is not None and self.price is not None and self.sale_price >= self.price:
            raise ValidationError({"sale_price": "قیمت ویژه باید کمتر از قیمت اصلی باشد."})
        if self.sale_starts_at and self.sale_ends_at and self.sale_ends_at <= self.sale_starts_at:
            raise ValidationError({"sale_ends_at": "پایان فروش ویژه باید بعد از شروع آن باشد."})

    def sale_is_active(self, now=None) -> bool:
        if self.sale_price is None:
            return False
        now = now or timezone.now()
        if self.sale_starts_at and now < self.sale_starts_at:
            return False
        return not (self.sale_ends_at and now >= self.sale_ends_at)

    def current_price(self, now=None) -> int:
        return self.sale_price if self.sale_is_active(now) else self.price

    def unit_price_basis(self) -> tuple[str, Decimal] | None:
        """(label, amount in base unit) for per-kg / per-liter comparison, or None."""
        amount = Decimal(self.package_amount)
        if self.package_unit == self.Unit.KILOGRAM:
            return "کیلوگرم", amount
        if self.package_unit == self.Unit.GRAM:
            return "کیلوگرم", amount / 1000
        if self.package_unit == self.Unit.LITER:
            return "لیتر", amount
        if self.package_unit == self.Unit.MILLILITER:
            return "لیتر", amount / 1000
        return None

    def unit_price(self, now=None) -> tuple[str, int] | None:
        """Informational price per kg/liter in rial, rounded to whole toman. Never the payable price."""
        basis = self.unit_price_basis()
        if not basis or basis[1] <= 0:
            return None
        label, base_amount = basis
        per_unit = Decimal(self.current_price(now)) / base_amount
        return label, int((per_unit / 10).quantize(Decimal("1"))) * 10

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.stock <= self.low_stock_threshold
