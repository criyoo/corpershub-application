from __future__ import annotations


def sync_subscription_plans_after_migrate(**kwargs):
    from apps.subscriptions.plan_sync import sync_subscription_plans

    sync_subscription_plans(using=kwargs["using"])
