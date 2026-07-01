from django.core.management.base import BaseCommand

from apps.payments.services import expire_stale_pending_transactions


class Command(BaseCommand):
    help = "Expire stale pending payment attempts."

    def handle(self, *args, **options):
        expired_count = expire_stale_pending_transactions()
        self.stdout.write(self.style.SUCCESS(f"Expired {expired_count} stale payment attempt(s)."))
