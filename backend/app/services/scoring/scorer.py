"""Deterministic, explainable fit scoring. Every component is a small, independently
unit-testable pure function returning a `(score 0-1, explanation)` pair -- no LLM call. This is
the architecture spec's core requirement: "do not ask an LLM to simply output an arbitrary
score." Semantic judgment an LLM could improve later (e.g. richer role/domain matching) can be
swapped into these component functions without touching the aggregation/persistence code.
"""

import re
from datetime import date

from app.domain_connections import detect_domain_connections
from app.schemas.candidate import CandidateProfile
from app.schemas.company import CompanyRead
from app.schemas.fit_score import FitScoreComponent, FitScoreResult, Tier
from app.schemas.job import JobRead
from app.schemas.search_profile import SearchProfileRead
from app.services.scoring.weights import WEIGHTS_VERSION, FitScoreWeights

_SKILL_SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "py": "python",
}

_AI_DATA_KEYWORDS = (
    "ai",
    "artificial intelligence",
    "machine learning",
    " ml ",
    "llm",
    "agentic",
    "data engineer",
    "data pipeline",
    "data infrastructure",
)

_TIER_THRESHOLDS: tuple[tuple[float, Tier], ...] = (
    (90, "excellent"),
    (80, "strong"),
    (70, "worth_reviewing"),
    (60, "weak"),
)
_STRENGTH_THRESHOLD = 0.7
_GAP_THRESHOLD = 0.4

_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*(?:-\s*\d+\s*)?years?", re.IGNORECASE)
_ENTRY_LEVEL_RE = re.compile(
    r"new grad|entry.level|0\s*-\s*2 years|no experience required", re.IGNORECASE
)


def _normalize_skill(name: str) -> str:
    lowered = name.strip().lower()
    return _SKILL_SYNONYMS.get(lowered, lowered)


def _tier_for(overall_score: float) -> Tier:
    for threshold, tier in _TIER_THRESHOLDS:
        if overall_score >= threshold:
            return tier
    return "ignore"


def _estimate_candidate_experience_years(candidate: CandidateProfile) -> float:
    """Sum of dated `work` experience durations. Deliberately falls back to 0 (never negative,
    never guessed higher) when nothing is dated -- e.g. a still-in-school candidate -- letting
    `_experience_match`'s smooth falloff do the rest rather than a hard rejection."""
    today = date.today()
    total_days = 0
    for exp in candidate.experiences:
        if exp.category != "work" or exp.start_date is None:
            continue
        end = exp.end_date or today
        total_days += max((end - exp.start_date).days, 0)
    return round(total_days / 365, 1) if total_days else 0.0


def _extract_min_years(requirements: str | None) -> float | None:
    if not requirements:
        return None
    match = _YEARS_RE.search(requirements)
    if match:
        return float(match.group(1))
    if _ENTRY_LEVEL_RE.search(requirements):
        return 0.0
    return None


class FitScorer:
    def score(
        self,
        *,
        candidate: CandidateProfile,
        job: JobRead,
        company: CompanyRead,
        profile: SearchProfileRead,
    ) -> FitScoreResult:
        weights = FitScoreWeights.from_profile_config(profile.config.weights)

        components = {
            "technical": self._technical_match(candidate, job),
            "role": self._role_match(job, profile),
            "ai_data": self._ai_data_match(candidate, job),
            "experience": self._experience_match(candidate, job),
            "stage": self._stage_match(company, profile),
            "location": self._location_match(job, profile),
            "domain": self._domain_match(company),
        }
        weight_map = weights.model_dump()
        weighted_sum = sum(components[key].score * weight_map[key] for key in components)
        overall_score = round(100 * weighted_sum / weights.total, 1) if weights.total else 0.0

        strengths = [c.explanation for c in components.values() if c.score >= _STRENGTH_THRESHOLD]
        gaps = [c.explanation for c in components.values() if c.score < _GAP_THRESHOLD]

        return FitScoreResult(
            **components,
            overall_score=overall_score,
            tier=_tier_for(overall_score),
            strengths=strengths,
            gaps=gaps,
            weights_version=WEIGHTS_VERSION,
        )

    @staticmethod
    def _technical_match(candidate: CandidateProfile, job: JobRead) -> FitScoreComponent:
        candidate_skills = {_normalize_skill(s.skill_name) for s in candidate.skills if s.verified}
        job_skills = {_normalize_skill(t) for t in job.technologies}
        if not job_skills:
            return FitScoreComponent(
                score=0.5, explanation="Job listed no specific technologies to compare against."
            )
        overlap = candidate_skills & job_skills
        score = min(len(overlap) / len(job_skills), 1.0)
        explanation = (
            f"Overlapping verified skills: {', '.join(sorted(overlap))}."
            if overlap
            else "No overlap between verified skills and the job's listed technologies."
        )
        return FitScoreComponent(score=score, explanation=explanation)

    @staticmethod
    def _role_match(job: JobRead, profile: SearchProfileRead) -> FitScoreComponent:
        role_filters = [r.lower() for r in profile.config.role_filters]
        if not role_filters:
            return FitScoreComponent(
                score=0.5, explanation="Profile has no role filters configured."
            )
        title = job.title.lower()
        matched_title = [r for r in role_filters if r in title]
        if matched_title:
            return FitScoreComponent(
                score=1.0,
                explanation=f"Job title matches desired role(s): {', '.join(matched_title)}.",
            )
        description = (job.description or "").lower()
        matched_description = [r for r in role_filters if r in description]
        if matched_description:
            return FitScoreComponent(
                score=0.6,
                explanation=(
                    f"Job description mentions desired role(s): "
                    f"{', '.join(matched_description)}, though not in the title."
                ),
            )
        return FitScoreComponent(
            score=0.2,
            explanation="Job title/description don't clearly match any configured role filter.",
        )

    @staticmethod
    def _ai_data_match(candidate: CandidateProfile, job: JobRead) -> FitScoreComponent:
        candidate_has_ai_data_skill = any(
            s.verified and s.category in ("ai", "data") for s in candidate.skills
        )
        haystack = f"{job.title} {job.description or ''} {' '.join(job.technologies)}".lower()
        hits = [k.strip() for k in _AI_DATA_KEYWORDS if k in haystack]
        if not hits:
            return FitScoreComponent(score=0.3, explanation="Job doesn't emphasize AI/data work.")
        if candidate_has_ai_data_skill:
            return FitScoreComponent(
                score=1.0,
                explanation=(
                    f"Job emphasizes AI/data work ({', '.join(hits[:3])}), matching the "
                    "candidate's verified AI/data experience."
                ),
            )
        return FitScoreComponent(
            score=0.5,
            explanation=(
                f"Job emphasizes AI/data work ({', '.join(hits[:3])}), but the candidate has no "
                "verified AI/data skill claims yet."
            ),
        )

    @staticmethod
    def _experience_match(candidate: CandidateProfile, job: JobRead) -> FitScoreComponent:
        candidate_years = _estimate_candidate_experience_years(candidate)
        required_years = _extract_min_years(job.experience_requirements)
        if required_years is None:
            return FitScoreComponent(
                score=0.7, explanation="Job listed no specific experience requirement."
            )
        gap = required_years - candidate_years
        if gap <= 0:
            return FitScoreComponent(
                score=1.0,
                explanation=f"Candidate meets or exceeds the ~{required_years:g}-year requirement.",
            )
        # Smooth falloff, not a cliff -- per spec, never auto-reject for asking slightly more
        # experience than the candidate has.
        score = max(0.3, round(1.0 - gap * 0.25, 2))
        return FitScoreComponent(
            score=score,
            explanation=(
                f"Job asks for ~{required_years:g} years; candidate has ~{candidate_years:g} -- "
                "not treated as an automatic disqualifier."
            ),
        )

    @staticmethod
    def _stage_match(company: CompanyRead, profile: SearchProfileRead) -> FitScoreComponent:
        stage_filters = [s.lower() for s in profile.config.stage_filters]
        if not stage_filters:
            return FitScoreComponent(
                score=0.5, explanation="Profile has no stage preference configured."
            )
        stage = (company.funding_stage or "").lower()
        if not stage or stage in ("unknown", "n/a"):
            return FitScoreComponent(score=0.4, explanation="Company funding stage unknown.")
        if stage in stage_filters:
            return FitScoreComponent(
                score=1.0,
                explanation=f"Company stage ({company.funding_stage}) matches profile preference.",
            )
        return FitScoreComponent(
            score=0.2,
            explanation=f"Company stage ({company.funding_stage}) is outside the preferred range.",
        )

    @staticmethod
    def _location_match(job: JobRead, profile: SearchProfileRead) -> FitScoreComponent:
        location_filters = [location.lower() for location in profile.config.location_filters]
        if not location_filters:
            return FitScoreComponent(
                score=0.5, explanation="Profile has no location filter configured."
            )
        haystack = f"{job.location or ''} {job.work_mode or ''}".lower()
        if any(location in haystack for location in location_filters):
            return FitScoreComponent(
                score=1.0,
                explanation=f"Job location/work mode matches: {job.location or job.work_mode}.",
            )
        if "remote" in haystack:
            return FitScoreComponent(
                score=0.7,
                explanation="Job is remote -- location-flexible even without an exact match.",
            )
        return FitScoreComponent(
            score=0.2,
            explanation=(
                f"Job location ({job.location or 'unspecified'}) doesn't match preferred locations."
            ),
        )

    @staticmethod
    def _domain_match(company: CompanyRead) -> FitScoreComponent:
        haystack = f"{company.industry or ''} {company.description or ''}"
        hits = detect_domain_connections(haystack)
        if hits:
            return FitScoreComponent(
                score=1.0, explanation=f"Genuine personal connection: {'; '.join(hits)}."
            )
        # Neutral, not a penalty: absence of a personal connection is the normal case, never a
        # candidate weakness -- per spec, these connections are a bonus signal only when
        # genuinely present, never something to force or treat as missing/lacking.
        return FitScoreComponent(
            score=0.5,
            explanation="No specific personal connection detected -- not every company needs one.",
        )
