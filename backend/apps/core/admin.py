from datetime import timedelta

from django.contrib import admin
from django.db.models import Sum

from apps.core.admin_fields import image_preview, toman
from apps.core.dates import tehran_today, to_jalali_str
from apps.core.models import FAQ, AuditLog, HomeBanner, Page, StoreSettings

admin.site.site_header = "پنل مدیریت فلاح و پسران"
admin.site.site_title = "مدیریت فلاح و پسران"
admin.site.index_title = "میز کار فروشگاه"


def _dashboard_context(request) -> dict:
    from apps.catalog.models import ProductVariant
    from apps.orders.models import Order
    from apps.reports import services as reports

    today = tehran_today()
    context = {
        "fs_awaiting_fulfillment": Order.objects.filter(
            status=Order.Status.CONFIRMED, fulfillment_status__in=["unfulfilled", "preparing"], is_test=False
        ).count(),
        "fs_needs_review": Order.objects.filter(needs_review=True).count(),
        "fs_low_stock": sum(
            1 for v in ProductVariant.objects.filter(is_active=True) if v.stock <= v.low_stock_threshold
        ),
        "fs_can_view_reports": request.user.has_perm("orders.view_financial_reports"),
    }
    if context["fs_can_view_reports"]:
        today_summary = reports.summary(today, today)
        context["fs_today_orders"] = today_summary.paid_orders
        context["fs_today_sales"] = toman(today_summary.customer_payments)
        week = reports.paid_orders(today - timedelta(days=6), today)
        context["fs_week_sales"] = toman(week.aggregate(t=Sum("grand_total"))["t"])
    return context


_original_index = admin.site.index


def _index(request, extra_context=None):
    context = _dashboard_context(request)
    context.update(extra_context or {})
    return _original_index(request, context)


admin.site.index = _index


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("اطلاعات عمومی", {"fields": ("store_name", "tagline", "announcement")}),
        ("راه‌های تماس", {"fields": ("phone", "email", "telegram_username", "address", "business_hours")}),
        ("فروش", {"fields": ("sales_enabled", "tax_rate_basis_points")}),
        ("سئو صفحهٔ اصلی", {"fields": ("seo_title", "seo_description")}),
    )

    def has_add_permission(self, request):
        return not StoreSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "is_active", "is_generated_sample", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_display_links = ("preview", "title")

    @admin.display(description="تصویر")
    def preview(self, obj):
        return image_preview(obj.image_desktop, 96)


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "requires_owner_review", "updated")
    list_filter = ("is_published", "requires_owner_review")
    search_fields = ("title", "body")

    @admin.display(description="آخرین ویرایش")
    def updated(self, obj):
        return to_jalali_str(obj.updated_at)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "group", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("group", "is_active")
    search_fields = ("question", "answer")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("when", "action", "object_type", "object_id", "message", "actor")
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "message")
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    @admin.display(description="زمان", ordering="created_at")
    def when(self, obj):
        return to_jalali_str(obj.created_at)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
