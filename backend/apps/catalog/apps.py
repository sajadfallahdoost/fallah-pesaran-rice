from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"
    verbose_name = "کاتالوگ محصولات"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from apps.core import revalidate

        for model_name in ("Category", "Product", "ProductImage", "ProductAttribute", "ProductVariant"):
            model = self.get_model(model_name)
            post_save.connect(revalidate.catalog_changed, sender=model)
            post_delete.connect(revalidate.catalog_changed, sender=model)
