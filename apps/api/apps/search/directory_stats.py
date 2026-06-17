from __future__ import annotations

from apps.accounts.models import User, UserRoleRegistrationTotal
from apps.accounts.presence import get_online_presence_cutoff
from apps.companies.models import CompanyProfile
from apps.corpers.models import CorperProfile


def build_directory_stats(*, role: str) -> dict[str, int]:
    if role == User.Role.COMPANY:
        approved_companies = CompanyProfile.objects.filter(
            verification_status=CompanyProfile.VerificationStatus.VERIFIED,
            approval_status=CompanyProfile.ApprovalStatus.APPROVED,
        ).filter(
            CompanyProfile.directory_visibility_q()
        )
        active_count = approved_companies.filter(user__is_active=True).count()
        total_count = approved_companies.count()
        online_count = approved_companies.filter(
            user__is_active=True,
            user__last_seen_at__gte=get_online_presence_cutoff(),
        ).count()
        return {
            "online_count": online_count,
            "active_count": active_count,
            "total_count": total_count,
        }

    if role == User.Role.CORPER:
        verified_corpers = CorperProfile.objects.filter(CorperProfile.directory_visibility_q())
        active_count = verified_corpers.filter(user__is_active=True).count()
        total_count = verified_corpers.count()
        online_count = verified_corpers.filter(
            user__is_active=True,
            user__last_seen_at__gte=get_online_presence_cutoff(),
        ).count()
        return {
            "online_count": online_count,
            "active_count": active_count,
            "total_count": total_count,
        }

    active_count = User.objects.filter(role=role, is_active=True).count()
    total_count = (
        UserRoleRegistrationTotal.objects.filter(role=role)
        .values_list("total_registered", flat=True)
        .first()
    )
    online_count = User.objects.filter(
        role=role,
        is_active=True,
        last_seen_at__gte=get_online_presence_cutoff(),
    ).count()

    return {
        "online_count": online_count,
        "active_count": active_count,
        "total_count": total_count or active_count,
    }
