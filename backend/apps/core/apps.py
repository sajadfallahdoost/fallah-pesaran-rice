from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "محتوا و تنظیمات"

    def ready(self):
        from django.db.models.signals import post_delete, post_migrate, post_save

        from apps.core import revalidate
        from apps.core.roles import ensure_roles

        # Every app's post_migrate: custom permissions of later apps (orders) must exist first.
        post_migrate.connect(ensure_roles, dispatch_uid="fallah_ensure_roles")
        for model_name in ("StoreSettings", "HomeBanner", "Page", "FAQ"):
            model = self.get_model(model_name)
            post_save.connect(revalidate.content_changed, sender=model)
            post_delete.connect(revalidate.content_changed, sender=model)
