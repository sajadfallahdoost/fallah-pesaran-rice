from django.conf import settings
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count, Max, Min, Sum
from django.utils.html import format_html

from apps.catalog.models import Category, Product, ProductAttribute, ProductImage, ProductVariant
from apps.core.admin_fields import TomanAdminMixin, image_preview, toman
from apps.core.models import audit


def save_variant_form(form, user) -> None:
    """Persist an admin edit without overwriting concurrent checkout reservations.

    Only changed fields are written; a stock edit is applied as a delta against the locked row.
    """
    obj = form.instance
    if not obj.pk:
        obj.save()
        return
    changed = [name for name in form.changed_data if name in {f.name for f in ProductVariant._meta.fields}]
    if not changed:
        return
    with transaction.atomic():
        current = ProductVariant.objects.select_for_update().get(pk=obj.pk)
        if "stock" in changed:
            delta = form.cleaned_data["stock"] - (form.initial.get("stock") or 0)
            obj.stock = max(0, current.stock + delta)
        obj.save(update_fields=[*changed, "updated_at"])
    audit(
        "variant_change",
        obj,
        f"ویرایش بستهٔ {obj.sku}",
        actor=user,
        fields=changed,
        stock=obj.stock,
        price=obj.price,
        sale_price=obj.sale_price,
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "preview",
        "name",
        "slug",
        "is_active",
        "show_in_navigation",
        "show_when_empty",
        "products",
        "sort_order",
    )
    list_display_links = ("preview", "name")
    list_editable = ("is_active", "show_in_navigation", "show_when_empty", "sort_order")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(product_total=Count("products"))

    @admin.display(description="تصویر")
    def preview(self, obj):
        return image_preview(obj.image, 56)

    @admin.display(description="محصولات", ordering="product_total")
    def products(self, obj):
        return obj.product_total


class VariantInline(TomanAdminMixin, admin.StackedInline):
    model = ProductVariant
    extra = 0
    min_num = 1
    toman_fields = ("price", "sale_price")
    fieldsets = (
        (None, {"fields": (("title", "sku"), ("package_amount", "package_unit", "shipping_weight_grams"))}),
        ("قیمت", {"fields": (("price", "sale_price"), ("sale_starts_at", "sale_ends_at"))}),
        ("موجودی", {"fields": (("stock", "low_stock_threshold"), ("is_active", "sort_order"))}),
    )


class ImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("preview", "image", "alt_text", "sort_order", "is_generated_sample")
    readonly_fields = ("preview",)

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        return image_preview(obj.image, 72)


class AttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1
    fields = ("name", "value", "sort_order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = (VariantInline, ImageInline, AttributeInline)
    list_display = (
        "thumb",
        "name",
        "category",
        "status",
        "is_sample",
        "is_featured",
        "price_range",
        "total_stock",
        "storefront",
    )
    list_display_links = ("thumb", "name")
    list_filter = ("status", "category", "is_sample", "is_featured")
    search_fields = ("name", "sku", "variants__sku", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("related_products",)
    readonly_fields = ("published_at", "storefront")
    actions = ("publish", "unpublish", "archive")
    save_on_top = True
    fieldsets = (
        (None, {"fields": ("name", "slug", "sku", "category", "status", "storefront")}),
        ("نمایش", {"fields": ("is_featured", "is_sample", "sort_order", "published_at")}),
        ("توضیحات", {"fields": ("short_description", "description", "storage_and_use")}),
        ("ارتباط و سئو", {"classes": ("collapse",), "fields": ("related_products", "seo_title", "seo_description")}),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("category")
            .prefetch_related("images")
            .annotate(
                min_price=Min("variants__price"), max_price=Max("variants__price"), stock_sum=Sum("variants__stock")
            )
        )

    @admin.display(description="تصویر")
    def thumb(self, obj):
        first = next(iter(obj.images.all()), None)
        return image_preview(first.image if first else None, 48)

    @admin.display(description="قیمت بسته‌ها", ordering="min_price")
    def price_range(self, obj):
        if obj.min_price is None:
            return "—"
        if obj.min_price == obj.max_price:
            return toman(obj.min_price)
        return f"{toman(obj.min_price)} تا {toman(obj.max_price)}"

    @admin.display(description="موجودی کل", ordering="stock_sum")
    def total_stock(self, obj):
        return obj.stock_sum or 0

    @admin.display(description="مشاهده در فروشگاه")
    def storefront(self, obj):
        if not obj or not obj.pk:
            return "—"
        label = "مشاهده" if obj.status == Product.Status.PUBLISHED else "فقط پس از انتشار"
        return format_html(
            '<a href="{}{}" target="_blank" rel="noopener">{}</a>',
            settings.PUBLIC_BASE_URL,
            obj.get_storefront_path(),
            label,
        )

    def _set_status(self, request, queryset, status, label):
        count = 0
        for product in queryset:
            product.status = status
            product.save()
            audit("product_status", product, f"{label}: {product.name}", actor=request.user)
            count += 1
        self.message_user(request, f"{count} محصول {label} شد.", messages.SUCCESS)

    @admin.action(description="انتشار محصولات انتخاب‌شده", permissions=["change"])
    def publish(self, request, queryset):
        if not settings.STORE_ALLOW_SAMPLE_SALES and queryset.filter(is_sample=True).exists():
            self.message_user(
                request,
                "محصولات نمونه در محیط فروش واقعی منتشر نمی‌شوند؛ ابتدا اطلاعات واقعی را وارد و "
                "تیک «محصول نمونه» را بردارید.",
                messages.ERROR,
            )
            return
        self._set_status(request, queryset, Product.Status.PUBLISHED, "منتشر")

    @admin.action(description="بازگرداندن به پیش‌نویس", permissions=["change"])
    def unpublish(self, request, queryset):
        self._set_status(request, queryset, Product.Status.DRAFT, "پیش‌نویس")

    @admin.action(description="بایگانی", permissions=["change"])
    def archive(self, request, queryset):
        self._set_status(request, queryset, Product.Status.ARCHIVED, "بایگانی")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and "status" in form.changed_data:
            audit("product_status", obj, f"وضعیت: {obj.get_status_display()}", actor=request.user)

    def save_formset(self, request, form, formset, change):
        if formset.model is not ProductVariant:
            return super().save_formset(request, form, formset, change)
        formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for variant_form in formset.forms:
            if variant_form in formset.deleted_forms or not variant_form.has_changed():
                continue
            variant_form.instance.product = form.instance
            save_variant_form(variant_form, request.user)


@admin.register(ProductVariant)
class ProductVariantAdmin(TomanAdminMixin, admin.ModelAdmin):
    """Quick list for daily price and stock updates."""

    toman_fields = ("price", "sale_price")
    list_display = ("__str__", "sku", "price_display", "stock", "low_stock_threshold", "is_active")
    list_editable = ("stock", "is_active")
    list_filter = ("is_active", "product__category", "product__status")
    search_fields = ("sku", "title", "product__name")
    list_select_related = ("product",)

    @admin.display(description="قیمت فعلی", ordering="price")
    def price_display(self, obj):
        current = obj.current_price()
        if current != obj.price:
            return f"{toman(current)} (اصلی {toman(obj.price)})"
        return toman(current)

    def save_model(self, request, obj, form, change):
        if change:
            save_variant_form(form, request.user)
        else:
            super().save_model(request, obj, form, change)
