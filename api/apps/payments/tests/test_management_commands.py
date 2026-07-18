from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase


class PaymentManagementCommandTests(SimpleTestCase):
    @patch("apps.payments.management.commands.expire_stale_payment_attempts.expire_stale_pending_transactions")
    def test_expire_stale_payment_attempts_command_runs_cleanup(self, mock_expire_stale_pending_transactions):
        mock_expire_stale_pending_transactions.return_value = 3
        stdout = StringIO()

        call_command("expire_stale_payment_attempts", stdout=stdout)

        mock_expire_stale_pending_transactions.assert_called_once_with()
        self.assertIn("Expired 3 stale payment attempt(s).", stdout.getvalue())
