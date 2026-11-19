from django.contrib import admin

from apps.accounts.models import Address, OtpCode
from apps.core.dates import to_jalali_str


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "province", "city", "user", "is_default")
    search_fields = ("full_name", "phone", "user__username", "city")
    list_filter = ("province",)
    raw_id_fields = ("user",)


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    """Codes are stored hashed; this view only helps diagnose delivery and abuse."""

    list_display = ("masked_phone", "created", "attempts", "consumed_at", "requester_ip")
    readonly_fields = ("phone", "created_at", "expires_at", "attempts", "consumed_at", "requester_ip")
    exclude = ("code_hash",)
    search_fields = ("phone",)

    @admin.display(description="موبایل")
    def masked_phone(self, obj):
        return f"{obj.phone[:4]}***{obj.phone[-2:]}"

    @admin.display(description="زمان", ordering="created_at")
    def created(self, obj):
        return to_jalali_str(obj.created_at)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
