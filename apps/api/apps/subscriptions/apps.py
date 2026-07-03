from django.apps import AppConfig
from django.db.models.signals import post_migrate


class SubscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.subscriptions"

    def ready(self):
        from apps.subscriptions.signals import sync_subscription_plans_after_migrate

        post_migrate.connect(
            sync_subscription_plans_after_migrate,
            sender=self,
            dispatch_uid="apps.subscriptions.sync_subscription_plans_after_migrate",
        )
