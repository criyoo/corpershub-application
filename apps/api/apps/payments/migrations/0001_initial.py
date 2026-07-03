import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('subscriptions', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentWebhookEvent',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('gateway', models.CharField(max_length=20)),
                ('event_id', models.CharField(max_length=120, unique=True)),
                ('event_type', models.CharField(max_length=120)),
                ('signature', models.CharField(blank=True, max_length=255)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('process_status', models.CharField(choices=[('received', 'Received'), ('processed', 'Processed'), ('failed', 'Failed')], default='received', max_length=20)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['gateway', 'process_status'], name='payments_pa_gateway_ec7a63_idx')],
            },
        ),
        migrations.CreateModel(
            name='PaymentTransaction',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('gateway', models.CharField(choices=[('flutterwave', 'Flutterwave'), ('card', 'Card')], max_length=20)),
                ('reference', models.CharField(max_length=120, unique=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('success', 'Success'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('amount_kobo', models.PositiveIntegerField()),
                ('currency', models.CharField(default='NGN', max_length=3)),
                ('idempotency_key', models.CharField(max_length=120, unique=True)),
                ('provider_payload', models.JSONField(blank=True, default=dict)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='subscriptions.usersubscription')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['gateway', 'status'], name='payments_pa_gateway_186290_idx')],
            },
        ),
        migrations.CreateModel(
            name="FlutterwavePaymentRecord",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tx_ref", models.CharField(max_length=120, unique=True)),
                ("flutterwave_transaction_id", models.CharField(blank=True, max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="NGN", max_length=3)),
                ("customer_email", models.EmailField(max_length=254)),
                ("status", models.CharField(default="pending", max_length=20)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                (
                    "internal_payment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="flutterwave_record",
                        to="payments.paymenttransaction",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["status", "verified_at"], name="payments_fl_status_11fb0d_idx")
                ],
            },
        ),
    ]
