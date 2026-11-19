from azbankgateways.admin import BankAdmin
from azbankgateways.models import Bank
from django.conf import settings
from django.contrib import admin, messages

from apps.core.admin_fields import toman
from apps.core.dates import to_jalali_str
from apps.payments.models import PaymentAttempt, PaymentProvider
from apps.payments.services import configured_provider_codes, reconcile_attempt


class ReadOnlyBankAdmin(BankAdmin):
    """The library's gateway records are evidence; nobody edits, adds, or deletes them."""

    readonly_fields = BankAdmin.fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.unregister(Bank)
admin.site.register(Bank, ReadOnlyBankAdmin)


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    list_display = ("display_name", "code", "is_enabled", "is_default", "credentials", "sort_order")
    list_editable = ("is_enabled", "sort_order")
    fields = ("code", "display_name", "description", "is_enabled", "is_default", "sort_order", "credentials")
    readonly_fields = ("credentials",)

    @admin.display(description="تنظیمات محرمانه روی سرور")
    def credentials(self, obj):
        if obj.code == "MOCK":
            return "درگاه آزمایشی (فقط محیط توسعه)" if settings.PAYMENT_MOCK_ENABLED else "غیرفعال در این محیط"
        return "تنظیم شده" if obj.code in configured_provider_codes() else "تنظیم نشده — درگاه نمایش داده نمی‌شود"


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "created",
        "provider",
        "status",
        "amount_display",
        "reference_number",
        "applied_to_order",
        "is_test",
    )
    list_filter = ("status", "provider", "is_test", "applied_to_order")
    search_fields = ("order__number", "reference_number", "tracking_code")
    readonly_fields = [f.name for f in PaymentAttempt._meta.fields]
    actions = ("recheck",)

    @admin.display(description="زمان", ordering="created_at")
    def created(self, obj):
        return to_jalali_str(obj.created_at)

    @admin.display(description="مبلغ", ordering="amount")
    def amount_display(self, obj):
        return toman(obj.amount)

    @admin.action(description="استعلام مجدد وضعیت از درگاه")
    def recheck(self, request, queryset):
        for attempt in queryset.filter(status__in=[PaymentAttempt.Status.UNKNOWN, PaymentAttempt.Status.REDIRECTED]):
            reconcile_attempt(attempt)
        self.message_user(request, "استعلام انجام شد؛ وضعیت‌ها را بررسی کنید.", messages.INFO)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
