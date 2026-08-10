import pytest
from pydantic import ValidationError

from app.schemas.llm_extraction import LLMSkillClaim


def test_skill_confidence_must_be_between_0_and_1() -> None:
    LLMSkillClaim(skill_name="Python", category="language", confidence=0.5, evidence=["x"])

    with pytest.raises(ValidationError):
        LLMSkillClaim(skill_name="Python", category="language", confidence=1.5, evidence=["x"])

    with pytest.raises(ValidationError):
        LLMSkillClaim(skill_name="Python", category="language", confidence=-0.1, evidence=["x"])


def test_skill_evidence_defaults_to_empty_list() -> None:
    claim = LLMSkillClaim(skill_name="Python", category="language", confidence=0.5)
    assert claim.evidence == []
