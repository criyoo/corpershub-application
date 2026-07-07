import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.common.models import SeededUser
from apps.companies.models import CompanyProfile
from apps.companies.services import ensure_company_profile
from apps.subscriptions.models import UserSubscription


class SeedDemoDataCommandTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.base_path = Path(self.temp_dir.name)

        self.company_photo_path = self.base_path / "airtel.webp"
        self.company_photo_path.write_bytes(b"company-image")
        self.corper_photo_path = self.base_path / "sharon.jpg"
        self.corper_photo_path.write_bytes(b"corper-image")

        self.company_seed_path = self.base_path / "default_companies.json"
        self.corper_seed_path = self.base_path / "default_corpers.json"

    def write_seed_files(self, *, company_email="airtel@example.com", corper_email="sharon@example.com"):
        company_payload = {
            "airtel": {
                "email": company_email,
                "password": "CompanyPass123!",
                "profile": {
                    "photo": str(self.company_photo_path),
                    "company_name": "Airtel Nigeria",
                    "company_registration_number": "RC 17872638",
                    "tax_identification_number": "3728172647316",
                    "organisation_type": "Public Organisation",
                    "sector": "Telecommunications",
                    "number_of_staff": "Above 1000",
                    "ppa_capacity": "3",
                    "number_of_office_location": "5",
                    "placement_type": "Part-Time/On-Site",
                    "monthly_allowance_offered": "N50,000-N100,000",
                    "ppa_support": "Yes",
                    "state": "Lagos",
                    "city": "Banana Island",
                    "preferred_state_of_deployment": ["Lagos", "Ogun"],
                    "company_summary": "A leading telecommunications company.",
                    "company_contact_details": {
                        "head_office_address": "1 Airtel Plaza",
                        "company_operation_address": "23 Airtel Drive",
                        "directors_name": "John Doe",
                        "directors_phone_number": "+234 801 234 5678",
                        "contact_name": "Jane Smith",
                        "contact_phone_number": "+234 802 345 6789",
                        "contact_email": "jane.smith@airtel.com",
                        "company_website": "https://airtel.com",
                    },
                    "corpers_requirement": {
                        "desired_qualifications": ["B.Sc", "M.Sc"],
                        "desired_age_range": "19-30",
                        "desired_field_of_study": ["Computer Science", "Information Technology"],
                        "desired_univeristies": ["University of Lagos"],
                        "desired_posting_states": ["Lagos", "Ogun"],
                        "desired_skills": ["data analysis", "networking"],
                        "desired_experience": "1 - 3 years experience in telecommunications.",
                    },
                },
            }
        }
        corper_payload = {
            "sharon": {
                "email": corper_email,
                "full_name": "Sharon Emmanuel",
                "password": "CorperPass123!",
                "verification_information": {
                    "date_of_birth": "13/03/2005",
                    "university_matriculation_number": "LAG/2020/54321",
                    "national_identifaction_number": "98736274637",
                    "nysc_callup_number": "NYSC/LAG/2026/123456",
                    "nysc_state_code": "NYSC/AB/24A/1234",
                },
                "profile": {
                    "photo": str(self.corper_photo_path),
                    "gender": "female",
                    "posting_state": "Lagos",
                    "batch": "B",
                    "stream": "1",
                    "mobile_number": "+2348061726475",
                    "field_of_study": "Agriculture",
                    "highest_degree": "B.Sc",
                    "university": "University of Port Harcourt",
                    "graduation_year": "2025",
                    "technical_skills": ["farming", "data analysis", "aeroponics"],
                    "soft_skills": ["communication", "teamwork"],
                    "language_spoken": ["English", "Hausa"],
                    "available_date": "12/07/2026",
                    "bio": "Sharon Emmanuel is a dedicated professional.",
                    "prefered_organisation": {
                        "preferred_sector": "Agriculture",
                        "prefered_organisation_type": "Private Organisation",
                        "Preferred_placement_type": "Full-time/Remote",
                        "preferred_monthly_allowance": "N20,000 - N50,000",
                    },
                },
            }
        }
        self.company_seed_path.write_text(json.dumps(company_payload))
        self.corper_seed_path.write_text(json.dumps(corper_payload))

    def test_seed_demo_data_skips_when_default_account_seeding_is_disabled(self):
        self.write_seed_files()

        with override_settings(
            SEED_DEFAULT_ACCOUNTS_ENABLED=False,
            SEED_COMPANY_DATA_PATH=str(self.company_seed_path),
            SEED_CORPER_DATA_PATH=str(self.corper_seed_path),
        ):
            call_command("seed_demo_data")

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(SeededUser.objects.count(), 0)

    def test_seed_demo_data_creates_seeded_company_and_corper_accounts_idempotently(self):
        self.write_seed_files()
        media_root = self.base_path / "media"
        media_root.mkdir()

        with override_settings(
            MEDIA_ROOT=str(media_root),
            SEED_COMPANY_DATA_PATH=str(self.company_seed_path),
            SEED_CORPER_DATA_PATH=str(self.corper_seed_path),
        ):
            call_command("seed_demo_data")
            call_command("seed_demo_data")

        self.assertEqual(User.objects.filter(role=User.Role.COMPANY).count(), 1)
        self.assertEqual(User.objects.filter(role=User.Role.CORPER).count(), 1)
        self.assertEqual(SeededUser.objects.count(), 2)

        company_user = User.objects.get(role=User.Role.COMPANY)
        company = company_user.company_profile
        self.assertEqual(company.company_name, "Airtel Nigeria")
        self.assertEqual(company.verification_status, company.VerificationStatus.VERIFIED)
        self.assertIsNotNone(company.terms_of_agreement_accepted_at)
        self.assertIsNotNone(company.terms_of_use_accepted_at)
        self.assertTrue(company.company_image.name.endswith("airtel.webp"))
        self.assertTrue(company.profile_fields_complete)
        self.assertTrue(company.is_complete)
        self.assertEqual(company.preferred_deployment_states, "Lagos, Ogun")
        self.assertEqual(company.organization_type, "Public Organisation")
        self.assertEqual(company.staff_count_range, "Above 1000")
        self.assertEqual(company.ppa_capacity, 3)
        self.assertEqual(company.office_location_count, 5)
        self.assertEqual(company.company_address, "23 Airtel Drive")
        self.assertEqual(company.head_office_address, "1 Airtel Plaza")
        self.assertEqual(company.contact_name, "Jane Smith")
        self.assertEqual(company.contact_email, "jane.smith@airtel.com")
        self.assertEqual(company.contact_phone, "+2348023456789")
        self.assertEqual(company.directors_name, "John Doe")
        self.assertEqual(company.director_phone_number, "+2348012345678")
        self.assertEqual(company.desired_qualification, "B.Sc, M.Sc")
        self.assertEqual(company.desired_field_of_study, "Computer Science, Information Technology")
        self.assertEqual(company.desired_university, "University of Lagos")
        self.assertEqual(company.desired_posting_states, "Lagos, Ogun")
        self.assertEqual(company.desired_skills, "data analysis, networking")

        corper_user = User.objects.get(role=User.Role.CORPER)
        corper = corper_user.corper_profile
        self.assertEqual(corper.full_name, "Sharon Emmanuel")
        self.assertEqual(corper.batch, "Batch B")
        self.assertEqual(corper.stream, "Stream 1")
        self.assertEqual(corper.verification_status, corper.VerificationStatus.VERIFIED)
        self.assertIsNotNone(corper.terms_of_agreement_accepted_at)
        self.assertIsNotNone(corper.terms_of_use_accepted_at)
        self.assertTrue(corper.profile_fields_complete)
        self.assertTrue(corper.is_complete)
        self.assertEqual(corper.skill, "farming, data analysis, aeroponics | communication, teamwork")
        self.assertEqual(corper.technical_skills, "farming, data analysis, aeroponics")
        self.assertEqual(corper.soft_skills, "communication, teamwork")
        self.assertEqual(corper.languages_spoken, "English, Hausa")
        self.assertEqual(str(corper.available_date), "2026-07-12")
        self.assertEqual(corper.preferred_sector, "Agriculture")
        self.assertEqual(corper.preferred_organization_type, "Private Organisation")
        self.assertEqual(corper.preferred_placement_type, "Full-time/Remote")
        self.assertEqual(corper.preferred_monthly_allowance, "N20,000 - N50,000")
        self.assertTrue(corper.profile_photo.name.endswith("sharon.jpg"))
        self.assertEqual(UserSubscription.objects.filter(user=corper_user).count(), 1)

    def test_seed_demo_data_updates_existing_seeded_users_when_fields_change(self):
        self.write_seed_files()
        media_root = self.base_path / "media"
        media_root.mkdir()

        with override_settings(
            MEDIA_ROOT=str(media_root),
            SEED_COMPANY_DATA_PATH=str(self.company_seed_path),
            SEED_CORPER_DATA_PATH=str(self.corper_seed_path),
        ):
            call_command("seed_demo_data")

            original_company_user = User.objects.get(role=User.Role.COMPANY)
            original_corper_user = User.objects.get(role=User.Role.CORPER)

            updated_company_payload = {
                "airtel": {
                    "email": "airtel-updated@example.com",
                    "password": "NewCompanyPass123!",
                    "profile": {
                        "photo": str(self.company_photo_path),
                        "company_name": "Airtel Nigeria Updated",
                        "company_registration_number": "RC 17872638",
                        "tax_identification_number": "3728172647316",
                        "organisation_type": "Private Organisation",
                        "sector": "Telecommunications",
                        "number_of_staff": "201-500",
                        "ppa_capacity": "6",
                        "number_of_office_location": "2",
                        "placement_type": "Full-Time/Hybrid",
                        "monthly_allowance_offered": "Negotiable",
                        "ppa_support": "Willing to discuss",
                        "state": "Abuja",
                        "city": "Wuse",
                        "preferred_state_of_deployment": ["Abuja", "Kaduna"],
                        "company_summary": "Updated company summary.",
                        "company_contact_details": {
                            "head_office_address": "44 Airtel HQ",
                            "company_operation_address": "44 Airtel Crescent",
                            "directors_name": "Ada Obi",
                            "directors_phone_number": "+234 803 111 2222",
                            "contact_name": "Kelechi Musa",
                            "contact_phone_number": "+234 804 333 4444",
                            "contact_email": "recruitment@airtel.ng",
                            "company_website": "https://airtel.ng",
                        },
                        "corpers_requirement": {
                            "desired_qualifications": ["B.Sc"],
                            "desired_age_range": "21-28",
                            "desired_field_of_study": ["Electrical Engineering"],
                            "desired_university": "Any university",
                            "desired_posting_state": "Abuja",
                            "desired_skills": ["fiber operations"],
                            "desired_experience": "Updated experience requirement.",
                        },
                    },
                }
            }
            updated_corper_payload = {
                "sharon": {
                    "email": "sharon-updated@example.com",
                    "full_name": "Sharon Emmanuel Updated",
                    "password": "NewCorperPass123!",
                    "verification_information": {
                        "date_of_birth": "2005-03-13",
                        "university_matriculation_number": "LAG/2020/99999",
                        "national_identifaction_number": "98736274637",
                        "nysc_callup_number": "NYSC/LAG/2026/654321",
                        "nysc_state_code": "NYSC/AB/24A/9999",
                    },
                    "profile": {
                        "photo": str(self.corper_photo_path),
                        "gender": "female",
                        "posting_state": "Abuja",
                        "batch": "C",
                        "stream": "2",
                        "mobile_number": "+2348061726475",
                        "field_of_study": "Computer Science",
                        "highest_degree": "M.Sc",
                        "university": "University of Lagos",
                        "graduation_year": "2026",
                        "technical_skills": ["python", "analytics"],
                        "soft_skills": ["communication"],
                        "language_spoken": ["English", "Yoruba"],
                        "available_date": "15/08/2026",
                        "bio": "Updated corper biography.",
                        "prefered_organisation": {
                            "preferred_sector": "Technology",
                            "prefered_organisation_type": "Private Organisation",
                            "Preferred_placement_type": "Hybrid",
                            "preferred_monthly_allowance": "N50,000 - N100,000",
                        },
                    },
                }
            }
            self.company_seed_path.write_text(json.dumps(updated_company_payload))
            self.corper_seed_path.write_text(json.dumps(updated_corper_payload))

            call_command("seed_demo_data")

        self.assertEqual(User.objects.filter(role=User.Role.COMPANY).count(), 1)
        self.assertEqual(User.objects.filter(role=User.Role.CORPER).count(), 1)

        company_user = User.objects.get(role=User.Role.COMPANY)
        corper_user = User.objects.get(role=User.Role.CORPER)
        self.assertEqual(company_user.id, original_company_user.id)
        self.assertEqual(corper_user.id, original_corper_user.id)
        self.assertEqual(company_user.email, "airtel-updated@example.com")
        self.assertEqual(corper_user.email, "sharon-updated@example.com")
        self.assertTrue(company_user.check_password("NewCompanyPass123!"))
        self.assertTrue(corper_user.check_password("NewCorperPass123!"))

        company = company_user.company_profile
        self.assertEqual(company.company_name, "Airtel Nigeria Updated")
        self.assertEqual(company.company_location_city, "Wuse")
        self.assertEqual(company.company_address, "44 Airtel Crescent")
        self.assertEqual(company.preferred_deployment_states, "Abuja, Kaduna")
        self.assertEqual(company.contact_name, "Kelechi Musa")
        self.assertEqual(company.contact_phone, "+2348043334444")
        self.assertEqual(company.desired_skills, "fiber operations")

        corper = corper_user.corper_profile
        self.assertEqual(corper.full_name, "Sharon Emmanuel Updated")
        self.assertEqual(corper.posting_location_state, "Abuja")
        self.assertEqual(corper.batch, "Batch C")
        self.assertEqual(corper.stream, "Stream 2")
        self.assertEqual(corper.field_of_study, "Computer Science")
        self.assertEqual(corper.degree, "M.Sc")
        self.assertEqual(corper.technical_skills, "python, analytics")
        self.assertEqual(corper.soft_skills, "communication")
        self.assertEqual(corper.languages_spoken, "English, Yoruba")
        self.assertEqual(str(corper.available_date), "2026-08-15")
        self.assertEqual(corper.skill, "python, analytics | communication")
        self.assertEqual(corper.preferred_sector, "Technology")
        self.assertEqual(corper.preferred_organization_type, "Private Organisation")
        self.assertEqual(corper.preferred_placement_type, "Hybrid")
        self.assertEqual(corper.preferred_monthly_allowance, "N50,000 - N100,000")
        self.assertEqual(corper.bio, "Updated corper biography.")

    def test_seed_demo_data_reuses_existing_company_profile_with_matching_unique_identifiers(self):
        self.write_seed_files()
        media_root = self.base_path / "media"
        media_root.mkdir()

        existing_user = User.objects.create_user(
            email="legacy-company@example.com",
            password="LegacyPass123!",
            role=User.Role.COMPANY,
            email_verified=True,
        )
        existing_company = ensure_company_profile(
            existing_user,
            company_name="Legacy Airtel",
            company_registration_number="RC17872638",
        )
        existing_company.tax_identification_number = "3728172647316"
        existing_company.save(update_fields=["tax_identification_number", "updated_at"])

        with override_settings(
            MEDIA_ROOT=str(media_root),
            SEED_COMPANY_DATA_PATH=str(self.company_seed_path),
            SEED_CORPER_DATA_PATH=str(self.corper_seed_path),
        ):
            call_command("seed_demo_data")

        seeded_user = User.objects.get(email="airtel@example.com")
        seeded_company = seeded_user.company_profile
        self.assertEqual(seeded_user.id, existing_user.id)
        self.assertEqual(seeded_company.id, existing_company.id)
        self.assertEqual(
            SeededUser.objects.get(seed_type=SeededUser.SeedType.COMPANY, seed_key="airtel").user_id,
            seeded_user.id,
        )
        self.assertEqual(
            CompanyProfile.objects.filter(company_registration_number="RC17872638").count(),
            1,
        )
        self.assertEqual(
            CompanyProfile.objects.filter(tax_identification_number="3728172647316").count(),
            1,
        )

    def test_seed_demo_data_clears_conflicting_company_identifiers_before_sync(self):
        self.write_seed_files()
        media_root = self.base_path / "media"
        media_root.mkdir()

        registration_user = User.objects.create_user(
            email="registration-conflict@example.com",
            password="ConflictPass123!",
            role=User.Role.COMPANY,
            email_verified=True,
        )
        registration_company = ensure_company_profile(
            registration_user,
            company_name="Registration Conflict",
            company_registration_number="RC17872638",
        )

        tax_user = User.objects.create_user(
            email="tax-conflict@example.com",
            password="ConflictPass123!",
            role=User.Role.COMPANY,
            email_verified=True,
        )
        tax_company = ensure_company_profile(
            tax_user,
            company_name="Tax Conflict",
            company_registration_number="RC99999999",
        )
        tax_company.tax_identification_number = "3728172647316"
        tax_company.save(update_fields=["tax_identification_number", "updated_at"])

        with override_settings(
            MEDIA_ROOT=str(media_root),
            SEED_COMPANY_DATA_PATH=str(self.company_seed_path),
            SEED_CORPER_DATA_PATH=str(self.corper_seed_path),
        ):
            call_command("seed_demo_data")

        seeded_user = User.objects.get(email="airtel@example.com")
        seeded_company = seeded_user.company_profile
        registration_company.refresh_from_db()
        tax_company.refresh_from_db()

        self.assertEqual(seeded_company.company_registration_number, "RC17872638")
        self.assertEqual(seeded_company.tax_identification_number, "3728172647316")
        self.assertEqual(registration_company.id, seeded_company.id)
        self.assertEqual(tax_company.tax_identification_number, "")
