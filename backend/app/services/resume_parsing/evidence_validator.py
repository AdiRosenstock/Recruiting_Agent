"""Deterministic cross-check of LLM-claimed evidence against the resume's actual raw text.

This is the enforcement point for "do not let the LLM invent experience": every skill's
evidence snippet is checked against `raw_text`, and a skill with no verified evidence has its
confidence downgraded (never silently dropped -- it stays visible with `verified=False` so a
human can still see and judge it in the dashboard later).
"""

from dataclasses import dataclass, field

from app.core.logging import log_agent_decision
from app.schemas.llm_extraction import LLMExtractedCandidateData, LLMSkillClaim
from app.services.evidence import verify_snippet

_UNVERIFIED_CONFIDENCE_CAP = 0.3


@dataclass(frozen=True)
class SkillValidation:
    verified: bool
    confidence: float
    evidence_verified: list[bool]


@dataclass(frozen=True)
class EvidenceValidationResult:
    skills: list[SkillValidation]
    education_verified: list[bool]
    experience_verified: list[bool]
    project_verified: list[bool]
    warnings: list[str] = field(default_factory=list)


class EvidenceValidator:
    def validate(self, data: LLMExtractedCandidateData, raw_text: str) -> EvidenceValidationResult:
        warnings: list[str] = []

        skill_results = [self._validate_skill(skill, raw_text, warnings) for skill in data.skills]

        education_verified = [
            self._validate_evidenced_entry(
                verify_snippet(edu.evidence_snippet, raw_text),
                f"Education entry '{edu.institution}'",
                warnings,
            )
            for edu in data.education
        ]
        experience_verified = [
            self._validate_evidenced_entry(
                verify_snippet(exp.evidence_snippet, raw_text),
                f"Experience entry '{exp.organization} - {exp.title}'",
                warnings,
            )
            for exp in data.experiences
        ]
        project_verified = [
            self._validate_evidenced_entry(
                verify_snippet(proj.evidence_snippet, raw_text),
                f"Project entry '{proj.name}'",
                warnings,
            )
            for proj in data.projects
        ]

        return EvidenceValidationResult(
            skills=skill_results,
            education_verified=education_verified,
            experience_verified=experience_verified,
            project_verified=project_verified,
            warnings=warnings,
        )

    @staticmethod
    def _validate_skill(
        skill: LLMSkillClaim, raw_text: str, warnings: list[str]
    ) -> SkillValidation:
        evidence_flags = [verify_snippet(snippet, raw_text) for snippet in skill.evidence]
        verified = any(evidence_flags)
        confidence = (
            skill.confidence if verified else min(skill.confidence, _UNVERIFIED_CONFIDENCE_CAP)
        )
        if not verified:
            warnings.append(
                f"Skill '{skill.skill_name}': no evidence snippet could be verified against "
                f"the resume text; confidence downgraded to {confidence:.2f}."
            )
            log_agent_decision(
                "skill_evidence_unverified",
                skill=skill.skill_name,
                original_confidence=skill.confidence,
                downgraded_to=confidence,
            )
        return SkillValidation(
            verified=verified, confidence=confidence, evidence_verified=evidence_flags
        )

    @staticmethod
    def _validate_evidenced_entry(verified: bool, label: str, warnings: list[str]) -> bool:
        if not verified:
            warnings.append(
                f"{label}: evidence snippet not found verbatim in the resume text -- kept, "
                "but flag for review."
            )
            log_agent_decision("entry_evidence_unverified", entry=label)
        return verified
