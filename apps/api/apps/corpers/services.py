from apps.accounts.models import User
from apps.corpers.models import CorperProfile


def ensure_corper_profile(user: User) -> CorperProfile:
    profile, _ = CorperProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": "",
            "first_name": "",
            "middle_name": "",
            "surname": "",
            "state_of_origin": "",
            "country_of_birth": "",
            "posting_location_state": "",
            "batch": "",
            "stream": "",
            "field_of_study": "",
            "degree": "",
            "university": "",
            "university_matriculation_number": "",
            "graduation_year": None,
            "mobile_number": "",
            "nysc_callup_number": "",
            "nysc_state_code": "",
            "skill": "",
            "technical_skills": "",
            "soft_skills": "",
            "languages_spoken": "",
            "available_date": None,
            "bio": "",
            "preferred_sector": "",
            "preferred_organization_type": "",
            "preferred_placement_type": "",
            "preferred_monthly_allowance": "",
            "preferred_organization_experience": "",
            "terms_of_agreement_accepted_at": None,
            "terms_of_use_accepted_at": None,
            "legal_acceptances": {},
            "directory_visibility_paused": False,
        },
    )
    return profile
