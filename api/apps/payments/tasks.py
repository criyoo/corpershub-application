from celery import shared_task

import logging

from apps.payments.services import expire_stale_pending_transactions, process_recorded_webhook_event

logger = logging.getLogger(__name__)


@shared_task
def expire_stale_payment_attempts_task() -> int:
    return expire_stale_pending_transactions()


@shared_task
def process_payment_webhook_event_task(event_id: str) -> None:
    try:
        process_recorded_webhook_event(event_id=event_id)
    except Exception:
        logger.exception("Failed to process payment webhook event.", extra={"event_id": event_id})
