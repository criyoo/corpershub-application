from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import EmailDomainRule, User
from apps.common.models import SeededUser
from apps.common.validators import normalize_mobile_number, normalize_nigerian_mobile_number_to_international
from apps.companies.models import CompanyProfile
from apps.companies.registration_lookup import normalize_company_registration_number
from apps.companies.services import ensure_company_profile
from apps.companies.validators import normalize_tax_identification_number
from apps.corpers.models import CorperProfile
from apps.corpers.services import ensure_corper_profile
from apps.subscriptions.plan_sync import sync_subscription_plans
from apps.subscriptions.services import ensure_trial_subscription

DEFAULT_COMPANY_SEED_PATH = "seed_data/companies/default_companies.json"
DEFAULT_CORPER_SEED_PATH = "seed_data/corpers/default_corpers.json"


class Command(BaseCommand):
    help = "Seed company and corper accounts from JSON files."

    def handle(self, *args, **options):
        if not getattr(settings, "SEED_DEFAULT_ACCOUNTS_ENABLED", False):
            self.stdout.write("SEED_DEFAULT_ACCOUNTS_ENABLED is false; skipping default account seed.")
            return

        EmailDomainRule.objects.get_or_create(domain="corpershub.ng", rule_type="allowlist")
        self.seed_subscription_plans()

        specs = [
            (
                SeededUser.SeedType.COMPANY,
                getattr(settings, "SEED_COMPANY_DATA_PATH", DEFAULT_COMPANY_SEED_PATH),
            ),
            (
                SeededUser.SeedType.CORPER,
                getattr(settings, "SEED_CORPER_DATA_PATH", DEFAULT_CORPER_SEED_PATH),
            ),
        ]

        created_users = 0
        updated_users = 0

        for seed_type, raw_path in specs:
            seed_path = self.resolve_path(raw_path)
            if not seed_path.exists():
                self.stdout.write(f"Seed file not found: {raw_path}")
                continue

            payload = json.loads(seed_path.read_text())
            if not isinstance(payload, dict):
                raise ValueError(f"Seed file {seed_path} must contain a JSON object at the top level.")

            for seed_key, entry in payload.items():
                if not isinstance(entry, dict):
                    raise ValueError(f"Seed entry {seed_key} in {seed_path} must be an object.")

                if seed_type == SeededUser.SeedType.COMPANY:
                    _, created = self.upsert_company(seed_key, entry)
                else:
                    _, created = self.upsert_corper(seed_key, entry)

                if created:
                    created_users += 1
                else:
                    updated_users += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed data synced successfully. Created {created_users} users and updated {updated_users} existing users."
            )
        )

    def seed_subscription_plans(self):
        sync_subscription_plans()

    def upsert_company(self, seed_key: str, entry: dict):
        profile_data = entry.get("profile") or {}
        requirement_data = profile_data.get("corpers_requirement") or {}
        contact_data = profile_data.get("company_contact_details") or {}

        company_name = self.clean_text(profile_data.get("company_name"))
        registration_number = normalize_company_registration_number(
            self.clean_text(profile_data.get("company_registration_number"))
        )
        tax_identification_number = normalize_tax_identification_number(
            self.clean_text(profile_data.get("tax_identification_number"))
        )
        existing_company = self.find_existing_company_profile(
            registration_number=registration_number,
            tax_identification_number=tax_identification_number,
        )
        user, created = self.upsert_seed_user(
            seed_type=SeededUser.SeedType.COMPANY,
            seed_key=seed_key,
            role=User.Role.COMPANY,
            email=self.clean_text(entry.get("email")).lower(),
            password=entry.get("password"),
            preferred_user=existing_company.user if existing_company is not None else None,
        )

        company = existing_company or ensure_company_profile(
            user,
            company_name=company_name,
            company_registration_number=registration_number,
        )
        if company.user_id != user.id:
            company.user = user
            company.save(update_fields=["user", "updated_at"])
        self.resolve_company_identifier_conflicts(
            company=company,
            registration_number=registration_number,
            tax_identification_number=tax_identification_number,
        )
        company.company_name = company_name
        company.company_registration_number = registration_number
        company.company_registration_date = (
            self.parse_date(profile_data.get("company_registration_date")) or timezone.now().date()
        )
        company.tax_identification_number = tax_identification_number
        company.company_location_state = self.clean_text(profile_data.get("state"))
        company.preferred_deployment_states = self.join_values(profile_data.get("preferred_state_of_deployment"))
        company.company_location_city = self.clean_text(profile_data.get("city"))
        company.company_address = self.clean_text(
            profile_data.get("company_address") or contact_data.get("company_operation_address")
        )
        company.head_office_address = self.clean_text(contact_data.get("head_office_address"))
        company.company_website = self.clean_text(contact_data.get("company_website"))
        company.company_sector = self.clean_text(profile_data.get("sector"))
        company.organization_type = self.clean_text(profile_data.get("organisation_type"))
        company.staff_count_range = self.clean_text(profile_data.get("number_of_staff"))
        company.ppa_capacity = self.parse_int(profile_data.get("ppa_capacity"))
        company.office_location_count = self.parse_int(profile_data.get("number_of_office_location"))
        company.company_function = self.clean_text(profile_data.get("company_function"))
        company.placement_type = self.clean_text(profile_data.get("placement_type"))
        company.monthly_allowance_offered = self.clean_text(profile_data.get("monthly_allowance_offered"))
        company.ppa_support = self.clean_text(profile_data.get("ppa_support"))
        company.desired_corper_description = self.clean_text(
            profile_data.get("desired_corper_description") or profile_data.get("company_summary")
        )
        company.desired_qualification = self.join_values(requirement_data.get("desired_qualifications"))
        company.desired_age_range = self.clean_text(requirement_data.get("desired_age_range"))
        company.desired_field_of_study = self.join_values(requirement_data.get("desired_field_of_study"))
        company.desired_university = (
            self.join_values(requirement_data.get("desired_universities"))
            or self.join_values(requirement_data.get("desired_univeristies"))
            or self.clean_text(requirement_data.get("desired_university"))
            or "Any university"
        )
        company.desired_posting_states = (
            self.join_values(requirement_data.get("desired_posting_states"))
            or self.clean_text(requirement_data.get("desired_posting_state"))
            or company.company_location_state
        )
        company.desired_skills = self.join_values(requirement_data.get("desired_skills"))
        company.desired_experience = self.clean_text(requirement_data.get("desired_experience"))
        company.contact_name = self.clean_text(contact_data.get("contact_name"))
        company.contact_email = self.clean_text(contact_data.get("contact_email")).lower()
        company.contact_phone = self.normalize_phone_number(contact_data.get("contact_phone_number"))
        company.directors_name = self.clean_text(contact_data.get("directors_name"))
        company.director_phone_number = self.normalize_phone_number(contact_data.get("directors_phone_number"))
        if not company.terms_of_agreement_accepted_at:
            company.terms_of_agreement_accepted_at = timezone.now()
        if not company.terms_of_use_accepted_at:
            company.terms_of_use_accepted_at = timezone.now()
        company.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        company.approval_status = CompanyProfile.ApprovalStatus.APPROVED

        photo_path = self.resolve_required_path(profile_data.get("photo"), f"company seed {seed_key} photo")
        self.sync_file_field(company, "company_image", photo_path)
        company.save()
        return company, created

    def upsert_corper(self, seed_key: str, entry: dict):
        profile_data = entry.get("profile") or {}
        verification_data = entry.get("verification_information") or {}
        preferred_organization_data = (
            profile_data.get("preferred_organisation") or profile_data.get("prefered_organisation") or {}
        )

        full_name = self.clean_text(entry.get("full_name")) or seed_key.replace("_", " ").title()
        user, created = self.upsert_seed_user(
            seed_type=SeededUser.SeedType.CORPER,
            seed_key=seed_key,
            role=User.Role.CORPER,
            email=self.clean_text(entry.get("email")).lower(),
            password=entry.get("password"),
        )

        corper = ensure_corper_profile(user)
        corper.full_name = full_name
        name_parts = [part for part in full_name.split() if part]
        corper.first_name = name_parts[0] if name_parts else ""
        corper.surname = name_parts[-1] if len(name_parts) > 1 else ""
        corper.middle_name = " ".join(name_parts[1:-1]) if len(name_parts) > 2 else ""
        corper.date_of_birth = self.parse_date(verification_data.get("date_of_birth"))
        corper.gender = self.clean_text(profile_data.get("gender")).lower()
        corper.state_of_origin = self.clean_text(verification_data.get("state_of_origin"))
        corper.country_of_birth = self.clean_text(verification_data.get("country_of_birth"))
        corper.posting_location_state = self.clean_text(profile_data.get("posting_state"))
        corper.batch = self.normalize_batch(profile_data.get("batch"))
        corper.stream = self.normalize_stream(profile_data.get("stream"))
        corper.university_matriculation_number = self.clean_text(
            verification_data.get("university_matriculation_number")
        )
        corper.field_of_study = self.clean_text(profile_data.get("field_of_study"))
        corper.degree = self.clean_text(profile_data.get("highest_degree"))
        corper.university = self.clean_text(profile_data.get("university"))
        corper.graduation_year = self.parse_int(profile_data.get("graduation_year"))
        corper.mobile_number = self.clean_text(profile_data.get("mobile_number"))
        corper.nin_number = self.clean_text(
            verification_data.get("national_identification_number")
            or verification_data.get("national_identifaction_number")
        )
        corper.nysc_callup_number = self.clean_text(verification_data.get("nysc_callup_number"))
        corper.nysc_state_code = self.clean_text(verification_data.get("nysc_state_code"))
        technical_skills = self.join_values(profile_data.get("technical_skills"))
        soft_skills = self.join_values(profile_data.get("soft_skills"))
        corper.technical_skills = technical_skills
        corper.soft_skills = soft_skills
        corper.languages_spoken = self.join_values(
            profile_data.get("languages_spoken") or profile_data.get("language_spoken")
        )
        corper.available_date = self.parse_date(profile_data.get("available_date"))
        corper.skill = self.combine_skill_summary(
            technical_skills,
            soft_skills,
            fallback=self.join_values(profile_data.get("skills")),
        )
        corper.bio = self.clean_text(profile_data.get("bio"))
        corper.preferred_sector = self.clean_text(preferred_organization_data.get("preferred_sector"))
        corper.preferred_organization_type = self.clean_text(
            preferred_organization_data.get("preferred_organization_type")
            or preferred_organization_data.get("preferred_organisation_type")
            or preferred_organization_data.get("prefered_organisation_type")
        )
        corper.preferred_placement_type = self.clean_text(
            preferred_organization_data.get("preferred_placement_type")
            or preferred_organization_data.get("Preferred_placement_type")
        )
        corper.preferred_monthly_allowance = self.clean_text(
            preferred_organization_data.get("preferred_monthly_allowance")
        )
        corper.preferred_organization_experience = self.clean_text(
            preferred_organization_data.get("preferred_organization_experience")
            or preferred_organization_data.get("preferred_organisation_experience")
        )
        corper.biodata_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nin_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_callup_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        corper.nysc_state_code_verification_status = CorperProfile.SensitiveStatus.VERIFIED
        if not corper.terms_of_agreement_accepted_at:
            corper.terms_of_agreement_accepted_at = timezone.now()
        if not corper.terms_of_use_accepted_at:
            corper.terms_of_use_accepted_at = timezone.now()
        corper.approval_status = CorperProfile.ApprovalStatus.APPROVED

        photo_path = self.resolve_required_path(profile_data.get("photo"), f"corper seed {seed_key} photo")
        self.sync_file_field(corper, "profile_photo", photo_path)
        corper.save()
        ensure_trial_subscription(user=user)
        return corper, created

    def upsert_seed_user(
        self,
        *,
        seed_type: str,
        seed_key: str,
        role: str,
        email: str,
        password: str | None,
        preferred_user: User | None = None,
    ):
        if not email:
            raise ValueError(f"Seed entry {seed_type}:{seed_key} is missing an email address.")

        seed_record = (
            SeededUser.objects.select_related("user")
            .filter(
                seed_type=seed_type,
                seed_key=seed_key,
            )
            .first()
        )
        if preferred_user is not None:
            user = preferred_user
            created = False
            SeededUser.objects.update_or_create(
                seed_type=seed_type,
                seed_key=seed_key,
                defaults={"user": user},
            )
        elif seed_record is not None:
            user = seed_record.user
            created = False
        else:
            user = User.objects.filter(email=email).first()
            created = user is None
            if user is None:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    role=role,
                    email_verified=True,
                    is_active=True,
                )
            SeededUser.objects.update_or_create(
                seed_type=seed_type,
                seed_key=seed_key,
                defaults={"user": user},
            )

        user.email = email
        user.role = role
        user.email_verified = True
        user.is_active = True
        if password:
            user.set_password(password)
        user.save()
        return user, created

    def find_existing_company_profile(
        self,
        *,
        registration_number: str,
        tax_identification_number: str,
    ) -> CompanyProfile | None:
        if registration_number and tax_identification_number:
            exact_match = (
                CompanyProfile.objects.select_related("user")
                .filter(
                    company_registration_number=registration_number,
                    tax_identification_number=tax_identification_number,
                )
                .order_by("created_at", "pk")
                .first()
            )
            if exact_match is not None:
                return exact_match

        if registration_number:
            registration_match = (
                CompanyProfile.objects.select_related("user")
                .filter(company_registration_number=registration_number)
                .order_by("created_at", "pk")
                .first()
            )
            if registration_match is not None:
                return registration_match

        if not tax_identification_number:
            return None
        return (
            CompanyProfile.objects.select_related("user")
            .filter(tax_identification_number=tax_identification_number)
            .order_by("created_at", "pk")
            .first()
        )

    def resolve_company_identifier_conflicts(
        self,
        *,
        company: CompanyProfile,
        registration_number: str,
        tax_identification_number: str,
    ) -> None:
        conflicts = CompanyProfile.objects.exclude(pk=company.pk).filter(
            Q(company_registration_number=registration_number) | Q(tax_identification_number=tax_identification_number)
        )
        for conflict in conflicts.iterator():
            updates = {}
            if registration_number and conflict.company_registration_number == registration_number:
                updates["company_registration_number"] = ""
            if tax_identification_number and conflict.tax_identification_number == tax_identification_number:
                updates["tax_identification_number"] = ""
            if updates:
                updates["updated_at"] = timezone.now()
                CompanyProfile.objects.filter(pk=conflict.pk).update(**updates)

    def sync_file_field(self, instance, field_name: str, file_path: Path):
        field = getattr(instance, field_name)
        current_name = Path(field.name).name if field else ""
        if current_name == file_path.name:
            return
        with file_path.open("rb") as fh:
            getattr(instance, field_name).save(file_path.name, File(fh), save=False)

    def parse_date(self, value):
        cleaned = self.clean_text(value)
        if not cleaned:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unsupported date format: {cleaned}")

    def parse_int(self, value):
        cleaned = self.clean_text(value)
        if not cleaned:
            return None
        return int(cleaned)

    def normalize_batch(self, value):
        cleaned = self.clean_text(value).upper()
        mapping = {
            "A": CorperProfile.Batch.BATCH_A,
            "B": CorperProfile.Batch.BATCH_B,
            "C": CorperProfile.Batch.BATCH_C,
            "BATCH A": CorperProfile.Batch.BATCH_A,
            "BATCH B": CorperProfile.Batch.BATCH_B,
            "BATCH C": CorperProfile.Batch.BATCH_C,
        }
        return mapping.get(cleaned, self.clean_text(value))

    def normalize_stream(self, value):
        cleaned = self.clean_text(value).upper()
        mapping = {
            "1": CorperProfile.Stream.STREAM_1,
            "2": CorperProfile.Stream.STREAM_2,
            "STREAM 1": CorperProfile.Stream.STREAM_1,
            "STREAM 2": CorperProfile.Stream.STREAM_2,
        }
        return mapping.get(cleaned, self.clean_text(value))

    def join_values(self, value):
        if isinstance(value, list):
            return ", ".join(self.clean_text(item) for item in value if self.clean_text(item))
        return self.clean_text(value)

    def combine_skill_summary(self, technical_skills: str, soft_skills: str, *, fallback: str = "") -> str:
        parts = []
        for value in (technical_skills, soft_skills):
            cleaned = self.clean_text(value)
            if cleaned and cleaned not in parts:
                parts.append(cleaned)
        return " | ".join(parts) or fallback

    def clean_text(self, value):
        return str(value or "").strip()

    def normalize_phone_number(self, value):
        cleaned = normalize_mobile_number(value)
        if not cleaned:
            return ""
        return normalize_nigerian_mobile_number_to_international(cleaned)

    def resolve_required_path(self, raw_path: str | None, label: str) -> Path:
        path = self.resolve_path(raw_path)
        if not path.exists():
            raise ValueError(f"Missing {label}: {raw_path}")
        return path

    def resolve_path(self, raw_path: str | None) -> Path:
        if not raw_path:
            return settings.BASE_DIR / "__missing_seed_path__"
        candidates = self.resolve_candidates(raw_path)
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def resolve_candidates(self, raw_path: str) -> list[Path]:
        raw = Path(str(raw_path))
        base_dir = settings.BASE_DIR
        repo_root = base_dir.parent.parent

        candidates = []
        if raw.is_absolute():
            candidates.append(raw)
        else:
            candidates.extend(
                [
                    base_dir / raw,
                    repo_root / raw,
                ]
            )
            raw_text = str(raw_path).strip()
            if "seed_data/" in raw_text:
                _, suffix = raw_text.split("seed_data/", 1)
                candidates.append(base_dir / "seed_data" / suffix)

        deduped = []
        seen = set()
        for candidate in candidates:
            resolved = Path(candidate)
            key = str(resolved)
            if key not in seen:
                deduped.append(resolved)
                seen.add(key)
        return deduped
