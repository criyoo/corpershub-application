from __future__ import annotations

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models
from apps.subscriptions.constants import SUBSCRIPTION_PLAN_PRICES as billing_plans

free, three, six, twelve = billing_plans.keys()


def configure_default_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")

    # Prices in kobo: N200=20000, N300=30000, N400=40000
    plans = [
        {
            "code": free,
            "name": "7 Days Free Trial",
            "description": "Browse companies for 7 days before moving to a paid corper plan.",
            "price_kobo": billing_plans[free],
            "currency": "NGN",
            "billing_interval": "trial",
            "applies_to": "corper",
            "features": ["7-day browsing access", "Dashboard access", "Notifications"],
            "is_active": True,
        },
        {
            "code": three,
            "name": "3 Months",
            "description": "One-off corper payment that unlocks full access for 3 months.",
            "price_kobo": billing_plans[three],
            "currency": "NGN",
            "billing_interval": "quarterly",
            "applies_to": "corper",
            "features": [
                "3 months of company browsing",
                "Company match scores",
                "Show interest to companies",
                "Realtime chat",
                "Notifications",
            ],
            "is_active": True,
        },
        {
            "code": six,
            "name": "6 Months",
            "description": "One-off corper payment that unlocks full access for 6 months.",
            "price_kobo": billing_plans[six],
            "currency": "NGN",
            "billing_interval": "semiannual",
            "applies_to": "corper",
            "features": [
                "6 months of company browsing",
                "Company match scores",
                "Show interest to companies",
                "Realtime chat",
                "Notifications",
            ],
            "is_active": True,
        },
        {
            "code": twelve,
            "name": "12 Months",
            "description": "One-off corper payment that unlocks full access for 12 months.",
            "price_kobo": billing_plans[twelve],
            "currency": "NGN",
            "billing_interval": "yearly",
            "applies_to": "corper",
            "features": [
                "12 months of company browsing",
                "Company match scores",
                "Show interest to companies",
                "Realtime chat",
                "Notifications",
            ],
            "is_active": True,
        },
    ]

    for plan in plans:
        SubscriptionPlan.objects.update_or_create(code=plan["code"], defaults=plan)


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.SlugField(unique=True)),
                ('name', models.CharField(max_length=120)),
                ('description', models.TextField(blank=True)),
                ('price_kobo', models.PositiveIntegerField(default=0)),
                ('currency', models.CharField(default='NGN', max_length=3)),
                ('billing_interval', models.CharField(choices=[('trial', '7 Days'), ('semiannual', '6 Months'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')], max_length=20)),
                ('applies_to', models.CharField(choices=[('company', 'Company'), ('corper', 'Corper'), ('both', 'Both')], default='company', max_length=20)),
                ('features', models.JSONField(blank=True, default=list)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['price_kobo', 'name'],
            },
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('trial', 'Trial'), ('active', 'Active'), ('past_due', 'Past Due'), ('cancelled', 'Cancelled'), ('expired', 'Expired')], default='trial', max_length=20)),
                ('starts_at', models.DateTimeField()),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('next_billing_at', models.DateTimeField(blank=True, null=True)),
                ('is_auto_renew', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='subscriptions.subscriptionplan')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subscriptions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', 'status'], name='subscriptio_user_id_28ce5e_idx')],
            },
        ),
        migrations.RunPython(configure_default_plans, migrations.RunPython.noop),
    ]