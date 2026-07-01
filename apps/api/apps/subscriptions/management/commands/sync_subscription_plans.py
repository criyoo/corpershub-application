from django.core.management.base import BaseCommand

from apps.subscriptions.plan_sync import sync_subscription_plans


class Command(BaseCommand):
    help = "Synchronize default subscription plans from code into the database."

    def handle(self, *args, **options):
        plan_count = sync_subscription_plans()
        self.stdout.write(self.style.SUCCESS(f"Synchronized {plan_count} subscription plans."))
