SHARED_LEGAL_DOCUMENT_SLUGS = (
    "acceptable-use-policy",
    "background-verification-consent",
    "cookies-policy",
    "ppa-placement-disclaimer",
    "privacy-policy",
    "terms-of-service",
)

CORPER_ONLY_LEGAL_DOCUMENT_SLUGS = ("corper-subscription-terms-payment-policy",)

CORPER_LEGAL_DOCUMENT_SLUGS = SHARED_LEGAL_DOCUMENT_SLUGS + CORPER_ONLY_LEGAL_DOCUMENT_SLUGS
COMPANY_LEGAL_DOCUMENT_SLUGS = SHARED_LEGAL_DOCUMENT_SLUGS
LEGAL_DOCUMENT_SLUGS = CORPER_LEGAL_DOCUMENT_SLUGS


def has_accepted_all_required_legal_documents(
    legal_acceptances: dict | None, required_slugs: tuple[str, ...] = LEGAL_DOCUMENT_SLUGS
) -> bool:
    acceptances = legal_acceptances or {}
    return all(bool((acceptances.get(slug) or {}).get("accepted_at")) for slug in required_slugs)
