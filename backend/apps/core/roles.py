"""Staff roles as Django groups, kept in sync after every migrate (idempotent)."""

from django.contrib.auth.models import Group, Permission

OWNER = "مالک فروشگاه"
ORDER_OPERATOR = "اپراتور سفارش"
CATALOG_EDITOR = "ویرایشگر کاتالوگ"

_CATALOG = [
    ("catalog", m, a)
    for m in ("category", "product", "productimage", "productattribute", "productvariant")
    for a in ("add", "change", "view", "delete")
]
_CONTENT = [("core", m, a) for m in ("homebanner", "page", "faq") for a in ("add", "change", "view", "delete")] + [
    ("core", "storesettings", "view"),
    ("core", "storesettings", "change"),
]
_SHIPPING = [
    ("shipping", m, a)
    for m in ("province", "shippingzone", "shippingmethod", "shippingrate")
    for a in ("add", "change", "view", "delete")
]
_ORDERS_VIEW = [
    ("orders", "order", "view"),
    ("orders", "order", "change"),
    ("orders", "shipment", "view"),
    ("orders", "invoice", "view"),
    ("orders", "refund", "view"),
    ("payments", "paymentattempt", "view"),
    ("accounts", "address", "view"),
]

ROLE_PERMISSIONS = {
    CATALOG_EDITOR: _CATALOG + _CONTENT,
    ORDER_OPERATOR: _ORDERS_VIEW
    + [
        ("orders", "order", "process_fulfillment"),
        ("catalog", "product", "view"),
        ("catalog", "productvariant", "view"),
    ],
    OWNER: _CATALOG
    + _CONTENT
    + _SHIPPING
    + _ORDERS_VIEW
    + [
        ("orders", "order", "process_fulfillment"),
        ("orders", "order", "manage_refunds"),
        ("orders", "order", "view_financial_reports"),
        ("payments", "paymentprovider", "view"),
        ("payments", "paymentprovider", "change"),
        ("azbankgateways", "bank", "view"),
        ("core", "auditlog", "view"),
        ("accounts", "otpcode", "view"),
    ],
}


def ensure_roles(**kwargs) -> None:
    for role, specs in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        perms = []
        for app_label, model, action in specs:
            codename = (
                action
                if action in {"process_fulfillment", "manage_refunds", "view_financial_reports"}
                else f"{action}_{model}"
            )
            perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if perm:
                perms.append(perm)
        group.permissions.set(perms)
