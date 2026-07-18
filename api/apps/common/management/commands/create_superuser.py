import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create a Django admin superuser from environment variables (idempotent)."

    def handle(self, *args, **options):
        email = (options.get("email") or "").strip()
        password = options.get("password") or ""

        if not email:
            for key in ("DJANGO_SUPERUSER_EMAIL", "DJANGO_SUPERUSER_USERNAME"):
                value = os.environ.get(key, "").strip()
                if value:
                    email = value
                    break

        if not password:
            password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "") or ""

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping superuser creation: DJANGO_SUPERUSER_EMAIL/USERNAME and "
                    "DJANGO_SUPERUSER_PASSWORD must be set."
                )
            )
            return

        if User.objects.filter(role=User.Role.ADMIN).exists():
            self.stdout.write("Admin user already exists, skipping superuser creation.")
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser created: {email}"))

    def add_arguments(self, parser):
        parser.add_argument("--email", help="Admin email address.")
        parser.add_argument("--password", help="Admin password.")
