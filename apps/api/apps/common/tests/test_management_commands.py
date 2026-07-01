from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class HasPendingMigrationsCommandTests(TestCase):
    def test_returns_success_when_no_migrations_are_pending(self):
        stdout = StringIO()

        call_command("has_pending_migrations", stdout=stdout)

        self.assertIn("No pending migrations.", stdout.getvalue())
