from django.contrib import admin

from apps.core.admin_fields import TomanAdminMixin, toman
from apps.shipping.models import Province, ShippingMethod, ShippingRate, ShippingZone


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    list_editable = ("sort_order",)
    search_fields = ("name",)


@admin.register(ShippingZone)
class ShippingZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "province_list", "city_names_short")
    filter_horizontal = ("provinces",)
    search_fields = ("name",)

    @admin.display(description="استان‌ها")
    def province_list(self, obj):
        names = [p.name for p in obj.provinces.all()]
        return "، ".join(names[:5]) + ("…" if len(names) > 5 else "")

    @admin.display(description="شهرها")
    def city_names_short(self, obj):
        return "، ".join(obj.city_list()) or "همهٔ شهرها"


class RateInline(TomanAdminMixin, admin.TabularInline):
    model = ShippingRate
    extra = 1
    toman_fields = ("base_cost", "per_extra_kg_cost", "free_shipping_threshold")
    fields = ("zone", "base_cost", "included_weight_grams", "per_extra_kg_cost", "free_shipping_threshold")


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    inlines = (RateInline,)
    list_display = ("name", "kind", "payment_timing", "is_active", "delivery_estimate", "rates_summary", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"code": ("name",)}
    fieldsets = (
        (None, {"fields": ("name", "code", "kind", "payment_timing", "is_active", "sort_order")}),
        ("نمایش به مشتری", {"fields": ("description", "delivery_estimate")}),
        ("محدودیت‌ها", {"fields": ("requires_address", "min_weight_grams", "max_weight_grams")}),
    )

    @admin.display(description="تعرفه‌ها")
    def rates_summary(self, obj):
        rates = list(obj.rates.select_related("zone"))
        if not rates:
            return "بدون تعرفه"
        return " | ".join(f"{r.zone.name}: {toman(r.base_cost)}" for r in rates[:3])
