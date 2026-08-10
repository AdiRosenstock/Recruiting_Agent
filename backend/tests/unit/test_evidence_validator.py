from app.schemas.llm_extraction import (
    LLMEducationClaim,
    LLMExperienceClaim,
    LLMExtractedCandidateData,
    LLMSkillClaim,
)
from app.services.resume_parsing.evidence_validator import EvidenceValidator, verify_snippet

RAW_TEXT = """\
Adi Rosenstock Gutreiman
BLOOMBERG Princeton, New Jersey
Data Engineer Summer Intern June 2026 - August 2026
Built a production Python/SQL data quality pipeline reconciling 2.3M+ financial records.
NORTHWESTERN UNIVERSITY Evanston, Illinois
Bachelor of Arts in Data Science and Economics.
"""


def test_verify_snippet_exact_match() -> None:
    assert verify_snippet("Built a production Python/SQL data quality pipeline", RAW_TEXT)


def test_verify_snippet_case_and_whitespace_insensitive() -> None:
    assert verify_snippet("built a production   python/sql data quality pipeline", RAW_TEXT)


def test_verify_snippet_fuzzy_near_match() -> None:
    # Minor formatting difference (extra space around the slash) vs a whole line -- should
    # still verify via the fuzzy fallback.
    assert verify_snippet("Data Engineer Summer Intern June 2026 -- August 2026 ", RAW_TEXT)


def test_verify_snippet_rejects_fabricated_text() -> None:
    assert not verify_snippet("Led a team of 50 engineers at Google", RAW_TEXT)


def test_verify_snippet_rejects_empty_string() -> None:
    assert not verify_snippet("", RAW_TEXT)


def test_validate_downgrades_confidence_for_unverified_skill() -> None:
    data = LLMExtractedCandidateData(
        full_name="Adi Rosenstock",
        skills=[
            LLMSkillClaim(
                skill_name="Python",
                category="language",
                confidence=0.95,
                evidence=["Built a production Python/SQL data quality pipeline"],
            ),
            LLMSkillClaim(
                skill_name="Kubernetes",
                category="tool",
                confidence=0.9,
                evidence=["Deployed to a 50-node Kubernetes cluster"],  # fabricated
            ),
        ],
    )

    result = EvidenceValidator().validate(data, RAW_TEXT)

    python_result, k8s_result = result.skills
    assert python_result.verified is True
    assert python_result.confidence == 0.95

    assert k8s_result.verified is False
    assert k8s_result.confidence <= 0.3
    assert any("Kubernetes" in w for w in result.warnings)


def test_validate_flags_unverified_experience_but_keeps_it() -> None:
    data = LLMExtractedCandidateData(
        full_name="Adi Rosenstock",
        experiences=[
            LLMExperienceClaim(
                category="work",
                organization="Bloomberg",
                title="Data Engineer Summer Intern",
                evidence_snippet="Built a production Python/SQL data quality pipeline",
            ),
            LLMExperienceClaim(
                category="work",
                organization="Fabricated Corp",
                title="Made Up Title",
                evidence_snippet="This text does not appear anywhere in the resume",
            ),
        ],
    )

    result = EvidenceValidator().validate(data, RAW_TEXT)

    assert result.experience_verified == [True, False]
    # Not rejected -- still flagged for human review via a warning.
    assert any("Fabricated Corp" in w for w in result.warnings)


def test_validate_education_verification() -> None:
    data = LLMExtractedCandidateData(
        full_name="Adi Rosenstock",
        education=[
            LLMEducationClaim(
                institution="Northwestern University",
                evidence_snippet="Bachelor of Arts in Data Science and Economics.",
            )
        ],
    )

    result = EvidenceValidator().validate(data, RAW_TEXT)

    assert result.education_verified == [True]
    assert result.warnings == []
