from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.subscriptions.services import corper_has_paid_access


TOKEN_RE = re.compile(r"[a-z0-9]+")
LIST_SPLIT_RE = re.compile(r"[,;\n]+")
AGE_RANGE_RE = re.compile(r"(?P<minimum>\d{2})\s*(?:-|to)\s*(?P<maximum>\d{2})")
AGE_FLOOR_RE = re.compile(r"(?P<minimum>\d{2})\s*\+")
AGE_CEILING_RE = re.compile(r"(?:under|below)\s*(?P<maximum>\d{2})")
YEAR_RANGE_RE = re.compile(r"(?P<minimum>(?:19|20)\d{2})\s*(?:-|to)\s*(?P<maximum>(?:19|20)\d{2})")
YEAR_FLOOR_RE = re.compile(r"(?P<minimum>(?:19|20)\d{2})\s*\+")
YEAR_CEILING_RE = re.compile(r"(?:under|below|before)\s*(?P<maximum>(?:19|20)\d{2})")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "candidate",
    "corper",
    "corpers",
    "corps",
    "experience",
    "for",
    "from",
    "ideal",
    "in",
    "into",
    "level",
    "looking",
    "member",
    "need",
    "needs",
    "nysc",
    "of",
    "our",
    "person",
    "preferred",
    "ready",
    "required",
    "requirements",
    "role",
    "someone",
    "that",
    "the",
    "this",
    "want",
    "wants",
    "with",
    "you",
    "your",
}
QUALIFICATION_PATTERNS = (
    ("b sc", "bsc"),
    ("b.sc", "bsc"),
    ("bsc", "bsc"),
    ("b tech", "btech"),
    ("b.tech", "btech"),
    ("btech", "btech"),
    ("hnd", "hnd"),
    ("ond", "ond"),
    ("ba", "ba"),
    ("b a", "ba"),
    ("msc", "msc"),
    ("m sc", "msc"),
    ("phd", "phd"),
)
QUALIFICATION_RANKS = {
    "ond": 1,
    "hnd": 2,
    "ba": 3,
    "bsc": 3,
    "btech": 3,
    "msc": 4,
    "phd": 5,
}
QUALIFICATION_MAX_POINTS = 12.0
FIELD_OF_STUDY_MAX_POINTS = 10.0
UNIVERSITY_MAX_POINTS = 8.0
POSTING_STATE_MAX_POINTS = 10.0
TECHNICAL_SKILLS_MAX_POINTS = 12.0
SOFT_SKILLS_MAX_POINTS = 8.0
AGE_MAX_POINTS = 8.0
EXPERIENCE_MAX_POINTS = 10.0
SECTOR_MAX_POINTS = 8.0
PLACEMENT_TYPE_MAX_POINTS = 7.0
MONTHLY_ALLOWANCE_MAX_POINTS = 7.0
RECOMMENDATION_THRESHOLD = 50
RECOMMENDATION_SIGNAL_THRESHOLD = 3


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    points: float
    reason: str | None


def viewer_can_see_corper_recommendations(viewer: User | None) -> bool:
    return bool(viewer and viewer.is_authenticated and viewer.role == User.Role.COMPANY)


def viewer_can_see_company_recommendations(viewer: User | None) -> bool:
    return bool(
        viewer and viewer.is_authenticated and viewer.role == User.Role.CORPER and corper_has_paid_access(user=viewer)
    )


def apply_corper_recommendations(*, viewer: User | None, corpers: Iterable[Any]) -> list[Any]:
    scored_corpers = list(corpers)
    if not viewer_can_see_corper_recommendations(viewer):
        return _attach_default_recommendations(scored_corpers)

    company = getattr(viewer, "company_profile", None)
    if company is None:
        return _attach_default_recommendations(scored_corpers)

    for corper in scored_corpers:
        score, reasons, signal_count = _score_corper_for_company(corper=corper, company=company)
        _attach_recommendation(corper, score=score, reasons=reasons, signal_count=signal_count)
    return scored_corpers


def apply_company_recommendations(*, viewer: User | None, companies: Iterable[Any]) -> list[Any]:
    scored_companies = list(companies)
    if not viewer_can_see_company_recommendations(viewer):
        return _attach_default_recommendations(scored_companies)

    corper = getattr(viewer, "corper_profile", None)
    if corper is None:
        return _attach_default_recommendations(scored_companies)

    for company in scored_companies:
        score, reasons, signal_count = _score_company_for_corper(corper=corper, company=company)
        _attach_recommendation(company, score=score, reasons=reasons, signal_count=signal_count)
    return scored_companies


def sort_by_recommendation(items: Iterable[Any], *, descending: bool = True) -> list[Any]:
    return sorted(
        items,
        key=lambda item: (
            getattr(item, "match_score_raw", 0.0),
            getattr(item, "match_signal_count", 0),
            getattr(item, "created_at", None),
        ),
        reverse=descending,
    )


def _attach_default_recommendations(items: list[Any]) -> list[Any]:
    for item in items:
        _attach_recommendation(item, score=0.0, reasons=[], signal_count=0)
    return items


def filter_corpers_for_directory(*, queryset: Any, params: Any) -> Any:
    queryset = _apply_corper_keyword_search(queryset, params.get("search"))

    text_filters = {
        "field_of_study": params.get("field_of_study"),
        "degree": params.get("degree"),
        "university": params.get("university"),
        "skill": params.get("skill") or params.get("skills"),
        "posting_location_state": params.get("posting_location_state")
        or params.get("posting_state")
        or params.get("state"),
        "gender": params.get("gender"),
    }
    for field_name, value in text_filters.items():
        cleaned = (value or "").strip()
        if cleaned:
            queryset = queryset.filter(**{f"{field_name}__icontains": cleaned})

    queryset = _apply_corper_age_filters(
        queryset,
        exact=params.get("age"),
        minimum=params.get("age_min"),
        maximum=params.get("age_max"),
    )
    queryset = _apply_graduation_year_filters(
        queryset,
        exact=params.get("graduation_year") or params.get("year"),
        minimum=params.get("graduation_year_min") or params.get("year_min"),
        maximum=params.get("graduation_year_max") or params.get("year_max"),
    )
    return queryset


def filter_companies_for_directory(*, queryset: Any, params: Any) -> Any:
    queryset = _apply_company_keyword_search(queryset, params.get("search"))

    text_filters = {
        "company_name": params.get("company_name") or params.get("name"),
        "company_location_state": params.get("company_location_state") or params.get("state"),
        "company_location_city": params.get("company_location_city") or params.get("city"),
        "company_sector": params.get("company_sector") or params.get("sector"),
        "company_function": params.get("company_function") or params.get("function"),
        "desired_field_of_study": params.get("desired_field_of_study"),
    }
    for field_name, value in text_filters.items():
        cleaned = (value or "").strip()
        if cleaned:
            queryset = queryset.filter(**{f"{field_name}__icontains": cleaned})

    return queryset


def _attach_recommendation(
    item: Any,
    *,
    score: float,
    reasons: list[str],
    signal_count: int,
) -> None:
    bounded_score = max(0.0, min(score, 100.0))
    rounded_score = int(round(bounded_score))
    item.match_score_raw = bounded_score
    item.match_score = rounded_score
    item.match_reasons = reasons[:4]
    item.match_signal_count = signal_count
    item.recommended = rounded_score >= RECOMMENDATION_THRESHOLD and signal_count >= RECOMMENDATION_SIGNAL_THRESHOLD


def _score_corper_for_company(*, corper: Any, company: Any) -> tuple[float, list[str], int]:
    components = [
        _qualification_component(
            corper_degree=corper.degree,
            desired_qualification=company.desired_qualification,
            exact_reason=f"Qualification matches {company.desired_qualification}.",
            compatible_reason=f"Qualification is compatible with {company.desired_qualification}.",
            close_reason=f"Qualification is close to the requested level of {company.desired_qualification}.",
        ),
        _location_component(
            corper_state=corper.posting_location_state,
            company_state=_company_posting_state_value(company),
            max_points=POSTING_STATE_MAX_POINTS,
            reason=f"Posting state matches {corper.posting_location_state}.",
        ),
        _age_component(
            age=corper.age,
            preferred_range=company.desired_age_range,
            in_range_reason=f"Age fits the preferred range of {company.desired_age_range}.",
            near_range_reason=f"Age is close to the preferred range of {company.desired_age_range}.",
        ),
        _field_of_study_component(
            corper_field_of_study=corper.field_of_study,
            desired_field_of_study=company.desired_field_of_study,
            exact_reason=f"Field of study directly matches {company.desired_field_of_study}.",
            partial_reason="Field of study partially aligns with the company preference.",
        ),
        _text_match_component(
            name="university",
            candidate_value=corper.university,
            desired_value=company.desired_university,
            max_points=UNIVERSITY_MAX_POINTS,
            exact_reason=f"University matches {company.desired_university}.",
            partial_reason="University partially aligns with the company preference.",
        ),
        _skills_component(
            name="technical_skills",
            desired_skills=company.desired_skills,
            evidence_texts=[corper.technical_skills, corper.skill, corper.bio],
            max_points=TECHNICAL_SKILLS_MAX_POINTS,
            reason_prefix="Technical skills matched",
        ),
        _skills_component(
            name="soft_skills",
            desired_skills=company.desired_skills,
            evidence_texts=[corper.soft_skills, corper.skill, corper.bio],
            max_points=SOFT_SKILLS_MAX_POINTS,
            reason_prefix="Soft skills matched",
        ),
        _coverage_component(
            name="experience",
            desired_value=company.desired_experience,
            evidence_texts=[
                corper.bio,
                corper.skill,
                corper.technical_skills,
                corper.soft_skills,
                getattr(corper, "preferred_organization_experience", ""),
            ],
            max_points=EXPERIENCE_MAX_POINTS,
            reason_prefix="Experience fit",
        ),
        _text_match_component(
            name="preferred_sector",
            preferred_value=getattr(corper, "preferred_sector", ""),
            company_value=company.company_sector,
            max_points=SECTOR_MAX_POINTS,
            exact_reason="Preferred industry/sector matches this company.",
            partial_reason="Preferred industry/sector partially aligns with this company.",
        ),
        _text_match_component(
            name="preferred_placement_type",
            preferred_value=getattr(corper, "preferred_placement_type", ""),
            company_value=company.placement_type,
            max_points=PLACEMENT_TYPE_MAX_POINTS,
            exact_reason="Preferred placement type matches this company.",
            partial_reason="Preferred placement type partially aligns with this company.",
        ),
        _allowance_component(
            name="preferred_monthly_allowance",
            preferred_value=getattr(corper, "preferred_monthly_allowance", ""),
            company_value=company.monthly_allowance_offered,
            max_points=MONTHLY_ALLOWANCE_MAX_POINTS,
            exact_reason="Preferred monthly allowance matches this company.",
            partial_reason="Preferred monthly allowance partially aligns with this company.",
        ),
    ]
    return _finalize_components(components)


def _score_company_for_corper(*, corper: Any, company: Any) -> tuple[float, list[str], int]:
    components = [
        _qualification_component(
            corper_degree=corper.degree,
            desired_qualification=company.desired_qualification,
            exact_reason=f"Your qualification matches {company.desired_qualification}.",
            compatible_reason=f"Your qualification is compatible with {company.desired_qualification}.",
            close_reason=f"Your qualification is close to the requested level of {company.desired_qualification}.",
        ),
        _location_component(
            corper_state=corper.posting_location_state,
            company_state=_company_posting_state_value(company),
            max_points=POSTING_STATE_MAX_POINTS,
            reason=f"Located in your posting state: {corper.posting_location_state}.",
        ),
        _age_component(
            age=corper.age,
            preferred_range=company.desired_age_range,
            in_range_reason=f"Your age fits the preferred range of {company.desired_age_range}.",
            near_range_reason=f"Your age is close to the preferred range of {company.desired_age_range}.",
        ),
        _field_of_study_component(
            corper_field_of_study=corper.field_of_study,
            desired_field_of_study=company.desired_field_of_study,
            exact_reason=f"Your field of study directly matches {company.desired_field_of_study}.",
            partial_reason="Your field of study partially aligns with the company preference.",
        ),
        _text_match_component(
            name="university",
            candidate_value=corper.university,
            desired_value=company.desired_university,
            max_points=UNIVERSITY_MAX_POINTS,
            exact_reason=f"Your university matches {company.desired_university}.",
            partial_reason="Your university partially aligns with the company preference.",
        ),
        _skills_component(
            name="technical_skills",
            desired_skills=company.desired_skills,
            evidence_texts=[corper.technical_skills, corper.skill, corper.bio],
            max_points=TECHNICAL_SKILLS_MAX_POINTS,
            reason_prefix="Requested technical skills matched",
        ),
        _skills_component(
            name="soft_skills",
            desired_skills=company.desired_skills,
            evidence_texts=[corper.soft_skills, corper.skill, corper.bio],
            max_points=SOFT_SKILLS_MAX_POINTS,
            reason_prefix="Requested soft skills matched",
        ),
        _coverage_component(
            name="experience",
            desired_value=company.desired_experience,
            evidence_texts=[
                corper.bio,
                corper.skill,
                corper.technical_skills,
                corper.soft_skills,
                getattr(corper, "preferred_organization_experience", ""),
            ],
            max_points=EXPERIENCE_MAX_POINTS,
            reason_prefix="Experience fit",
        ),
        _text_match_component(
            name="preferred_sector",
            preferred_value=getattr(corper, "preferred_sector", ""),
            company_value=company.company_sector,
            max_points=SECTOR_MAX_POINTS,
            exact_reason="Matches your preferred industry/sector.",
            partial_reason="Partially aligns with your preferred industry/sector.",
        ),
        _text_match_component(
            name="preferred_placement_type",
            preferred_value=getattr(corper, "preferred_placement_type", ""),
            company_value=company.placement_type,
            max_points=PLACEMENT_TYPE_MAX_POINTS,
            exact_reason="Matches your preferred placement type.",
            partial_reason="Partially aligns with your preferred placement type.",
        ),
        _allowance_component(
            name="preferred_monthly_allowance",
            preferred_value=getattr(corper, "preferred_monthly_allowance", ""),
            company_value=company.monthly_allowance_offered,
            max_points=MONTHLY_ALLOWANCE_MAX_POINTS,
            exact_reason="Matches your preferred monthly allowance.",
            partial_reason="Partially aligns with your preferred monthly allowance.",
        ),
    ]
    return _finalize_components(components)


def _finalize_components(components: list[ScoreComponent]) -> tuple[float, list[str], int]:
    total_score = sum(component.points for component in components)
    positive_components = [component for component in components if component.points > 0 and component.reason]
    ordered_reasons = [
        component.reason
        for component in sorted(positive_components, key=lambda component: component.points, reverse=True)
        if component.reason
    ]
    signal_count = sum(1 for component in components if component.points > 0)
    return total_score, _dedupe(ordered_reasons), signal_count


def _qualification_component(
    *,
    corper_degree: str | None,
    desired_qualification: str | None,
    exact_reason: str,
    compatible_reason: str,
    close_reason: str,
) -> ScoreComponent:
    corper_rank = _highest_qualification_rank(corper_degree)
    desired_ranks = _extract_qualification_ranks(desired_qualification)
    if corper_rank is None or not desired_ranks:
        return ScoreComponent("qualification", 0.0, None)

    if corper_rank in desired_ranks:
        return ScoreComponent("qualification", QUALIFICATION_MAX_POINTS, exact_reason)

    highest_desired_rank = max(desired_ranks)
    lowest_desired_rank = min(desired_ranks)
    if corper_rank > highest_desired_rank:
        distance = corper_rank - highest_desired_rank
        points = max(QUALIFICATION_MAX_POINTS * 0.75, QUALIFICATION_MAX_POINTS - (distance * 2.0))
        return ScoreComponent("qualification", points, compatible_reason)

    if corper_rank >= lowest_desired_rank:
        return ScoreComponent("qualification", QUALIFICATION_MAX_POINTS * 0.9, compatible_reason)

    if lowest_desired_rank - corper_rank == 1:
        return ScoreComponent("qualification", QUALIFICATION_MAX_POINTS * 0.4, close_reason)

    return ScoreComponent("qualification", 0.0, None)


def _location_component(
    *,
    corper_state: str | None,
    company_state: str | None,
    max_points: float,
    reason: str,
) -> ScoreComponent:
    normalized_corper_state = _normalized(corper_state)
    if not normalized_corper_state:
        return ScoreComponent("location", 0.0, None)

    company_states = [
        normalized_state
        for normalized_state in (_normalized(state) for state in LIST_SPLIT_RE.split(company_state or ""))
        if normalized_state
    ]
    if normalized_corper_state in company_states:
        return ScoreComponent("location", max_points, reason)
    return ScoreComponent("location", 0.0, None)


def _company_posting_state_value(company: Any) -> str | None:
    return (
        getattr(company, "desired_posting_states", "")
        or getattr(company, "preferred_deployment_states", "")
        or getattr(company, "company_location_state", "")
    )


def _age_component(
    *,
    age: int | None,
    preferred_range: str | None,
    in_range_reason: str,
    near_range_reason: str,
) -> ScoreComponent:
    if age is None:
        return ScoreComponent("age", 0.0, None)

    bounds = _parse_age_range(preferred_range)
    if bounds is None:
        return ScoreComponent("age", 0.0, None)

    minimum, maximum = bounds
    if minimum is not None and maximum is not None:
        if minimum <= age <= maximum:
            midpoint = (minimum + maximum) / 2
            half_span = max((maximum - minimum) / 2, 1)
            closeness = 1 - (abs(age - midpoint) / (half_span + 1))
            ratio = 0.75 + (max(0.0, closeness) * 0.25)
            return ScoreComponent("age", AGE_MAX_POINTS * ratio, in_range_reason)

        distance = minimum - age if age < minimum else age - maximum
        if distance == 1:
            return ScoreComponent("age", AGE_MAX_POINTS * 0.45, near_range_reason)
        if distance == 2:
            return ScoreComponent("age", AGE_MAX_POINTS * 0.2, near_range_reason)
        return ScoreComponent("age", 0.0, None)

    if minimum is not None:
        if age >= minimum:
            return ScoreComponent("age", AGE_MAX_POINTS, in_range_reason)
        if minimum - age == 1:
            return ScoreComponent("age", AGE_MAX_POINTS * 0.45, near_range_reason)
        return ScoreComponent("age", 0.0, None)

    if maximum is not None:
        if age <= maximum:
            return ScoreComponent("age", AGE_MAX_POINTS, in_range_reason)
        if age - maximum == 1:
            return ScoreComponent("age", AGE_MAX_POINTS * 0.45, near_range_reason)
        return ScoreComponent("age", 0.0, None)

    return ScoreComponent("age", 0.0, None)


def _field_of_study_component(
    *,
    corper_field_of_study: str | None,
    desired_field_of_study: str | None,
    exact_reason: str,
    partial_reason: str,
) -> ScoreComponent:
    return _text_match_component(
        name="field_of_study",
        candidate_value=corper_field_of_study,
        desired_value=desired_field_of_study,
        max_points=FIELD_OF_STUDY_MAX_POINTS,
        exact_reason=exact_reason,
        partial_reason=partial_reason,
    )


def _skills_component(
    *,
    name: str,
    desired_skills: str | None,
    evidence_texts: list[str | None],
    max_points: float,
    reason_prefix: str,
) -> ScoreComponent:
    coverage_ratio, matched_phrases = _phrase_coverage(desired_skills, evidence_texts)
    if coverage_ratio <= 0:
        return ScoreComponent(name, 0.0, None)

    reason = f"{reason_prefix} {round(coverage_ratio * 100)}%: {_join_terms(matched_phrases)}."
    return ScoreComponent(name, max_points * coverage_ratio, reason)


def _coverage_component(
    *,
    name: str,
    desired_value: str | None,
    evidence_texts: list[str | None],
    max_points: float,
    reason_prefix: str,
) -> ScoreComponent:
    coverage_ratio, matched_phrases = _phrase_coverage(desired_value, evidence_texts)
    if coverage_ratio < 0.2:
        return ScoreComponent(name, 0.0, None)

    if matched_phrases:
        reason = f"{reason_prefix} {round(coverage_ratio * 100)}%: {_join_terms(matched_phrases)}."
    else:
        reason = f"{reason_prefix} {round(coverage_ratio * 100)}%."
    return ScoreComponent(name, max_points * coverage_ratio, reason)


def _text_match_component(
    *,
    name: str,
    candidate_value: str | None = None,
    desired_value: str | None = None,
    preferred_value: str | None = None,
    company_value: str | None = None,
    max_points: float,
    exact_reason: str,
    partial_reason: str,
) -> ScoreComponent:
    left_value = candidate_value if candidate_value is not None else preferred_value
    right_value = desired_value if desired_value is not None else company_value
    similarity = _best_phrase_similarity(left_value, right_value)
    if similarity >= 0.95:
        return ScoreComponent(name, max_points, exact_reason)
    if similarity >= 0.35:
        return ScoreComponent(name, max_points * similarity, partial_reason)
    return ScoreComponent(name, 0.0, None)


def _allowance_component(
    *,
    name: str,
    preferred_value: str | None,
    company_value: str | None,
    max_points: float,
    exact_reason: str,
    partial_reason: str,
) -> ScoreComponent:
    preferred_allowance = _parse_allowance_range(preferred_value)
    company_allowance = _parse_allowance_range(company_value)
    if preferred_allowance and company_allowance:
        preferred_min, preferred_max, preferred_negotiable = preferred_allowance
        company_min, company_max, company_negotiable = company_allowance
        if preferred_negotiable and company_negotiable:
            return ScoreComponent(name, max_points, exact_reason)
        if preferred_negotiable or company_negotiable:
            return ScoreComponent(name, max_points * 0.5, partial_reason)

        if preferred_min == company_min and preferred_max == company_max:
            return ScoreComponent(name, max_points, exact_reason)

        overlap_ratio = _range_overlap_ratio(
            preferred_min,
            preferred_max,
            company_min,
            company_max,
        )
        if overlap_ratio > 0:
            return ScoreComponent(
                name,
                max_points * (0.65 + (0.35 * overlap_ratio)),
                partial_reason,
            )

        if _range_gap(preferred_min, preferred_max, company_min, company_max) <= 25000:
            return ScoreComponent(name, max_points * 0.35, partial_reason)

    return _text_match_component(
        name=name,
        preferred_value=preferred_value,
        company_value=company_value,
        max_points=max_points,
        exact_reason=exact_reason,
        partial_reason=partial_reason,
    )


def _phrase_coverage(desired_value: str | None, evidence_texts: list[str | None]) -> tuple[float, list[str]]:
    desired_phrases = _extract_phrases(desired_value)
    evidence_candidates = [value for value in evidence_texts if value]
    combined_evidence = " ".join(evidence_candidates).strip()
    if combined_evidence:
        evidence_candidates.append(combined_evidence)

    if not desired_phrases or not evidence_candidates:
        return 0.0, []

    scored_phrases: list[tuple[str, float]] = []
    for phrase in desired_phrases:
        best_score = max(
            (_phrase_similarity(candidate, phrase) for candidate in evidence_candidates),
            default=0.0,
        )
        scored_phrases.append((phrase, best_score))

    coverage_ratio = sum(score for _, score in scored_phrases) / len(scored_phrases)
    matched_phrases = [
        phrase for phrase, score in sorted(scored_phrases, key=lambda item: item[1], reverse=True) if score >= 0.35
    ]
    return min(coverage_ratio, 1.0), matched_phrases[:3]


def _best_phrase_similarity(left_value: str | None, right_value: str | None) -> float:
    left_phrases = _extract_phrases(left_value)
    right_phrases = _extract_phrases(right_value)
    if not left_phrases or not right_phrases:
        return _phrase_similarity(left_value, right_value)

    return max(
        (
            _phrase_similarity(left_phrase, right_phrase)
            for left_phrase in left_phrases
            for right_phrase in right_phrases
        ),
        default=0.0,
    )


def _phrase_similarity(candidate_value: str | None, desired_value: str | None) -> float:
    candidate = _normalized(candidate_value)
    desired = _normalized(desired_value)
    if not candidate or not desired:
        return 0.0

    if candidate == desired:
        return 1.0
    if desired in candidate or candidate in desired:
        return 0.95

    candidate_tokens = set(_tokenize(candidate))
    desired_tokens = set(_tokenize(desired))
    if not candidate_tokens or not desired_tokens:
        return 0.0

    overlap = candidate_tokens & desired_tokens
    if not overlap:
        return 0.0

    desired_coverage = len(overlap) / len(desired_tokens)
    candidate_coverage = len(overlap) / len(candidate_tokens)
    return min(1.0, (desired_coverage * 0.75) + (candidate_coverage * 0.25))


def _highest_qualification_rank(value: str | None) -> int | None:
    qualifications = _extract_qualifications(value)
    if not qualifications:
        return None
    return max(QUALIFICATION_RANKS[qualification] for qualification in qualifications)


def _extract_qualification_ranks(value: str | None) -> set[int]:
    return {
        QUALIFICATION_RANKS[qualification]
        for qualification in _extract_qualifications(value)
        if qualification in QUALIFICATION_RANKS
    }


def _extract_qualifications(value: str | None) -> set[str]:
    normalized = _normalized(value)
    if not normalized:
        return set()

    padded = f" {normalized} "
    qualifications = {token for token in _tokenize(normalized) if token in {"hnd", "ond", "msc", "phd"}}
    for pattern, canonical in QUALIFICATION_PATTERNS:
        if f" {pattern} " in padded:
            qualifications.add(canonical)
    return qualifications


def _parse_age_range(value: str | None) -> tuple[int | None, int | None] | None:
    if not value:
        return None

    normalized = _normalized(value)
    if not normalized:
        return None

    between_match = AGE_RANGE_RE.search(normalized)
    if between_match:
        return int(between_match.group("minimum")), int(between_match.group("maximum"))

    floor_match = AGE_FLOOR_RE.search(normalized)
    if floor_match:
        return int(floor_match.group("minimum")), None

    ceiling_match = AGE_CEILING_RE.search(normalized)
    if ceiling_match:
        return None, int(ceiling_match.group("maximum")) - 1

    return None


def _parse_year_range(value: str | None) -> tuple[int | None, int | None] | None:
    if not value:
        return None

    normalized = _normalized(value)
    if not normalized:
        return None

    between_match = YEAR_RANGE_RE.search(normalized)
    if between_match:
        return int(between_match.group("minimum")), int(between_match.group("maximum"))

    floor_match = YEAR_FLOOR_RE.search(normalized)
    if floor_match:
        return int(floor_match.group("minimum")), None

    ceiling_match = YEAR_CEILING_RE.search(normalized)
    if ceiling_match:
        return None, int(ceiling_match.group("maximum")) - 1

    if normalized.isdigit() and len(normalized) == 4:
        year = int(normalized)
        return year, year

    return None


def _apply_corper_keyword_search(queryset: Any, value: str | None) -> Any:
    normalized = _normalized(value)
    if not normalized:
        return queryset

    remaining = normalized
    graduation_year_bounds, remaining = _extract_year_bounds(remaining)
    if graduation_year_bounds is not None:
        queryset = _filter_by_graduation_year_bounds(queryset, *graduation_year_bounds)

    age_bounds, remaining = _extract_age_bounds(remaining)
    if age_bounds is not None:
        queryset = _filter_corpers_by_age_bounds(queryset, *age_bounds)

    for term in _extract_search_terms(remaining):
        if term.isdigit() and len(term) == 4:
            queryset = queryset.filter(graduation_year=int(term))
            continue

        if term.isdigit() and len(term) == 2:
            queryset = _filter_corpers_by_age_bounds(queryset, int(term), int(term))
            continue

        queryset = queryset.filter(_corper_text_query(term))

    return queryset


def _apply_company_keyword_search(queryset: Any, value: str | None) -> Any:
    normalized = _normalized(value)
    if not normalized:
        return queryset

    for term in _extract_search_terms(normalized):
        queryset = queryset.filter(_company_text_query(term))
    return queryset


def _corper_text_query(term: str) -> Q:
    return (
        Q(full_name__icontains=term)
        | Q(posting_location_state__icontains=term)
        | Q(field_of_study__icontains=term)
        | Q(degree__icontains=term)
        | Q(university__icontains=term)
        | Q(skill__icontains=term)
        | Q(bio__icontains=term)
        | Q(preferred_sector__icontains=term)
        | Q(preferred_organization_type__icontains=term)
        | Q(preferred_placement_type__icontains=term)
        | Q(preferred_monthly_allowance__icontains=term)
        | Q(preferred_organization_experience__icontains=term)
        | Q(gender__icontains=term)
    )


def _company_text_query(term: str) -> Q:
    return (
        Q(company_name__icontains=term)
        | Q(company_location_state__icontains=term)
        | Q(company_location_city__icontains=term)
        | Q(company_sector__icontains=term)
        | Q(company_function__icontains=term)
        | Q(desired_field_of_study__icontains=term)
        | Q(desired_university__icontains=term)
        | Q(desired_posting_states__icontains=term)
        | Q(desired_corper_description__icontains=term)
    )


def _apply_corper_age_filters(
    queryset: Any,
    *,
    exact: str | None,
    minimum: str | None,
    maximum: str | None,
) -> Any:
    parsed_bounds = _parse_age_range(exact)
    if parsed_bounds is not None:
        return _filter_corpers_by_age_bounds(queryset, *parsed_bounds)

    if (exact or "").strip().isdigit():
        age = int(exact.strip())
        return _filter_corpers_by_age_bounds(queryset, age, age)

    min_age = _safe_int(minimum)
    max_age = _safe_int(maximum)
    if min_age is None and max_age is None:
        return queryset
    return _filter_corpers_by_age_bounds(queryset, min_age, max_age)


def _apply_graduation_year_filters(
    queryset: Any,
    *,
    exact: str | None,
    minimum: str | None,
    maximum: str | None,
) -> Any:
    parsed_bounds = _parse_year_range(exact)
    if parsed_bounds is not None:
        return _filter_by_graduation_year_bounds(queryset, *parsed_bounds)

    min_year = _safe_int(minimum)
    max_year = _safe_int(maximum)
    if min_year is None and max_year is None:
        return queryset
    return _filter_by_graduation_year_bounds(queryset, min_year, max_year)


def _filter_by_graduation_year_bounds(
    queryset: Any,
    minimum: int | None,
    maximum: int | None,
) -> Any:
    if minimum is not None and maximum is not None:
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        return queryset.filter(graduation_year__range=(minimum, maximum))

    if minimum is not None:
        return queryset.filter(graduation_year__gte=minimum)

    if maximum is not None:
        return queryset.filter(graduation_year__lte=maximum)

    return queryset


def _filter_corpers_by_age_bounds(
    queryset: Any,
    minimum: int | None,
    maximum: int | None,
) -> Any:
    if minimum is not None and maximum is not None and minimum > maximum:
        minimum, maximum = maximum, minimum

    today = timezone.localdate()
    if minimum is not None:
        youngest_birthdate = _years_ago(today, minimum)
        queryset = queryset.filter(date_of_birth__lte=youngest_birthdate)

    if maximum is not None:
        oldest_birthdate = _shift_days(_years_ago(today, maximum + 1), 1)
        queryset = queryset.filter(date_of_birth__gte=oldest_birthdate)

    return queryset


def _extract_year_bounds(value: str) -> tuple[tuple[int | None, int | None] | None, str]:
    return _extract_bounds(value, YEAR_RANGE_RE, YEAR_FLOOR_RE, YEAR_CEILING_RE, _parse_year_range)


def _extract_age_bounds(value: str) -> tuple[tuple[int | None, int | None] | None, str]:
    return _extract_bounds(value, AGE_RANGE_RE, AGE_FLOOR_RE, AGE_CEILING_RE, _parse_age_range)


def _extract_bounds(
    value: str,
    range_pattern: re.Pattern[str],
    floor_pattern: re.Pattern[str],
    ceiling_pattern: re.Pattern[str],
    parser: Any,
) -> tuple[tuple[int | None, int | None] | None, str]:
    for pattern in (range_pattern, floor_pattern, ceiling_pattern):
        match = pattern.search(value)
        if not match:
            continue

        bounds = parser(match.group(0))
        remaining = _normalized(f"{value[: match.start()]} {value[match.end() :]}")
        return bounds, remaining

    return None, value


def _extract_search_terms(value: str) -> list[str]:
    terms: list[str] = []
    for term in TOKEN_RE.findall(value):
        if term.isdigit():
            terms.append(term)
            continue
        if len(term) >= 2 and term not in STOP_WORDS:
            terms.append(term)
    return terms


def _years_ago(reference_date: Any, years: int) -> Any:
    try:
        return reference_date.replace(year=reference_date.year - years)
    except ValueError:
        return reference_date.replace(month=2, day=28, year=reference_date.year - years)


def _shift_days(reference_date: Any, days: int) -> Any:
    return reference_date + timedelta(days=days)


def _safe_int(value: str | None) -> int | None:
    cleaned = (value or "").strip()
    if not cleaned or not cleaned.lstrip("+-").isdigit():
        return None
    return int(cleaned)


def _parse_allowance_range(value: str | None) -> tuple[int | None, int | None, bool] | None:
    normalized = _normalized(value)
    if not normalized:
        return None
    if "negotiable" in normalized:
        return None, None, True
    if normalized == "none":
        return 0, 0, False

    amounts = [int(amount) for amount in re.findall(r"\d[\d,]*", str(value or "").replace(",", ""))]
    if not amounts:
        return None

    if "below" in normalized:
        return 0, amounts[0], False
    if "above" in normalized:
        return amounts[0], None, False
    if len(amounts) >= 2:
        minimum, maximum = sorted(amounts[:2])
        return minimum, maximum, False
    return amounts[0], amounts[0], False


def _range_overlap_ratio(
    left_min: int | None,
    left_max: int | None,
    right_min: int | None,
    right_max: int | None,
) -> float:
    normalized_left_min = 0 if left_min is None else left_min
    normalized_left_max = float("inf") if left_max is None else left_max
    normalized_right_min = 0 if right_min is None else right_min
    normalized_right_max = float("inf") if right_max is None else right_max

    overlap_start = max(normalized_left_min, normalized_right_min)
    overlap_end = min(normalized_left_max, normalized_right_max)
    if overlap_end < overlap_start:
        return 0.0
    if overlap_end == overlap_start:
        return 0.2

    left_span = (
        normalized_left_max - normalized_left_min
        if normalized_left_max != float("inf")
        else max(overlap_end - overlap_start, 1)
    )
    right_span = (
        normalized_right_max - normalized_right_min
        if normalized_right_max != float("inf")
        else max(overlap_end - overlap_start, 1)
    )
    denominator = max(min(left_span, right_span), 1)
    return min(1.0, (overlap_end - overlap_start) / denominator)


def _range_gap(
    left_min: int | None,
    left_max: int | None,
    right_min: int | None,
    right_max: int | None,
) -> int:
    normalized_left_min = 0 if left_min is None else left_min
    normalized_left_max = float("inf") if left_max is None else left_max
    normalized_right_min = 0 if right_min is None else right_min
    normalized_right_max = float("inf") if right_max is None else right_max
    if normalized_left_max < normalized_right_min:
        return int(normalized_right_min - normalized_left_max)
    if normalized_right_max < normalized_left_min:
        return int(normalized_left_min - normalized_right_max)
    return 0


def _extract_phrases(value: str | None) -> list[str]:
    if not value:
        return []

    raw_parts = [part.strip() for part in LIST_SPLIT_RE.split(value) if part.strip()]
    if not raw_parts:
        raw_parts = [value.strip()]

    phrases: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        normalized = _normalized(part)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        phrases.append(part.strip())
    return phrases


def _tokenize(value: str | None) -> list[str]:
    if not value:
        return []
    tokens = TOKEN_RE.findall(_normalized(value))
    return [token for token in tokens if len(token) > 2 and token not in STOP_WORDS]


def _join_terms(terms: list[str]) -> str:
    if not terms:
        return "relevant evidence found"
    return ", ".join(term.strip() for term in terms[:3])


def _normalized(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("/", " ")
    normalized = re.sub(r"[^a-z0-9+\-\s.]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
