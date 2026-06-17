from __future__ import annotations

from typing import Any

from apps.audit.models import AuditLog


def log_audit_event(*, actor=None, action: str, target_type: str, target_id: str = "", metadata: dict[str, Any] | None = None):
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )
