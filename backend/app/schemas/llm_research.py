"""The schema an LLM is constrained to fill when researching a company from fetched page text.
Mirrors `schemas.llm_extraction`'s trust boundary: facts must carry a verbatim quote (checked
deterministically, same pattern as resume evidence -- see services/research/agent.py);
inferences are the only place synthesis is allowed, and are always persisted as inferences, never
silently promoted to facts.
"""

from pydantic import BaseModel, Field

# what_they_build | customers | problem | funding | founders | product_direction | launch |
# engineering_challenge | other
_FACT_TYPE_DESC = (
    "One of: what_they_build, customers, problem, funding, founders, product_direction, "
    "launch, engineering_challenge, other"
)


class LLMResearchFact(BaseModel):
    fact_type: str = Field(description=_FACT_TYPE_DESC)
    statement: str = Field(description="A concise factual statement.")
    evidence: str = Field(
        description="A literal, verbatim quote from the provided page text supporting this fact."
    )


class LLMResearchInference(BaseModel):
    fact_type: str = Field(description=_FACT_TYPE_DESC)
    statement: str = Field(description="A concise, reasonable inference -- not a verbatim quote.")
    reasoning: str = Field(description="One sentence on why this inference is reasonable.")


class LLMCompanyResearchData(BaseModel):
    facts: list[LLMResearchFact] = Field(default_factory=list)
    inferences: list[LLMResearchInference] = Field(default_factory=list)
