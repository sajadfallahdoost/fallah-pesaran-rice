from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import Category, Product, ProductVariant


def media_url(field) -> str | None:
    return field.url if field else None


def stock_status(variant: ProductVariant) -> str:
    if variant.stock <= 0:
        return "out_of_stock"
    if variant.is_low_stock:
        return "low_stock"
    return "in_stock"


class CategorySerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    product_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "image",
            "image_alt",
            "product_count",
            "show_in_navigation",
            "seo_title",
            "seo_description",
            "updated_at",
        )

    def get_image(self, obj):
        return media_url(obj.image)


class VariantSerializer(serializers.ModelSerializer):
    unit_label = serializers.CharField(source="get_package_unit_display")
    price = serializers.SerializerMethodField()
    list_price = serializers.IntegerField(source="price")
    on_sale = serializers.SerializerMethodField()
    sale_ends_at = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    low_stock_count = serializers.SerializerMethodField()
    max_quantity = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "title",
            "sku",
            "package_amount",
            "package_unit",
            "unit_label",
            "price",
            "list_price",
            "on_sale",
            "sale_ends_at",
            "stock_status",
            "low_stock_count",
            "max_quantity",
            "unit_price",
            "shipping_weight_grams",
        )

    def get_price(self, obj):
        return obj.current_price(self.context.get("now"))

    def get_on_sale(self, obj):
        return obj.sale_is_active(self.context.get("now"))

    def get_sale_ends_at(self, obj):
        return obj.sale_ends_at if obj.sale_is_active(self.context.get("now")) else None

    def get_stock_status(self, obj):
        return stock_status(obj)

    def get_low_stock_count(self, obj):
        return obj.stock if obj.is_low_stock else None

    def get_max_quantity(self, obj):
        return max(0, min(obj.stock, 50))

    def get_unit_price(self, obj):
        unit = obj.unit_price(self.context.get("now"))
        return {"label": unit[0], "amount": unit[1]} if unit else None


def _active_variants(product: Product) -> list[ProductVariant]:
    return [v for v in product.variants.all() if v.is_active]


def _purchasable(product: Product) -> tuple[bool, str]:
    if product.is_sample and not settings.STORE_ALLOW_SAMPLE_SALES:
        return False, "این محصول نمونهٔ نمایشی است و تا تأیید اطلاعات واقعی فروخته نمی‌شود."
    return True, ""


class ProductCardSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    price_from = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    variant_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "short_description",
            "is_sample",
            "image",
            "price_from",
            "in_stock",
            "variant_count",
            "updated_at",
        )

    def get_category(self, obj):
        return {"name": obj.category.name, "slug": obj.category.slug}

    def get_image(self, obj):
        images = list(obj.images.all())
        if not images:
            return None
        first = images[0]
        return {"url": first.image.url, "alt": first.alt_text, "is_generated_sample": first.is_generated_sample}

    def get_price_from(self, obj):
        now = self.context.get("now") or timezone.now()
        variants = _active_variants(obj)
        if not variants:
            return None
        cheapest = min(variants, key=lambda v: v.current_price(now))
        unit = cheapest.unit_price(now)
        return {
            "price": cheapest.current_price(now),
            "list_price": cheapest.price,
            "on_sale": cheapest.sale_is_active(now),
            "variant_title": cheapest.title,
            "unit_price": {"label": unit[0], "amount": unit[1]} if unit else None,
        }

    def get_in_stock(self, obj):
        return any(v.stock > 0 for v in _active_variants(obj))

    def get_variant_count(self, obj):
        return len(_active_variants(obj))


class ProductDetailSerializer(ProductCardSerializer):
    images = serializers.SerializerMethodField()
    attributes = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()
    related = serializers.SerializerMethodField()
    purchasable = serializers.SerializerMethodField()

    class Meta(ProductCardSerializer.Meta):
        fields = ProductCardSerializer.Meta.fields + (
            "sku",
            "description",
            "storage_and_use",
            "images",
            "attributes",
            "variants",
            "related",
            "purchasable",
            "seo_title",
            "seo_description",
            "updated_at",
        )

    def get_images(self, obj):
        return [
            {"url": img.image.url, "alt": img.alt_text, "is_generated_sample": img.is_generated_sample}
            for img in obj.images.all()
        ]

    def get_attributes(self, obj):
        return [{"name": a.name, "value": a.value} for a in obj.attributes.all()]

    def get_variants(self, obj):
        return VariantSerializer(_active_variants(obj), many=True, context=self.context).data

    def get_related(self, obj):
        related = [p for p in obj.related_products.all() if p.status == Product.Status.PUBLISHED]
        return ProductCardSerializer(related[:4], many=True, context=self.context).data

    def get_purchasable(self, obj):
        ok, reason = _purchasable(obj)
        return {"ok": ok, "reason": reason}
