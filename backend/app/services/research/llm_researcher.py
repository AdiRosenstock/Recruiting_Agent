"""LLM-powered step: turn a fetched company page's text into FACT/INFERENCE claims. Versioned
prompt (see `PROMPT_VERSION`), same pattern as services/resume_parsing/llm_structurer.py.
"""

from app.schemas.llm_research import LLMCompanyResearchData
from app.services.llm.base import LLMProvider

PROMPT_VERSION = "company_researcher_v1"

SYSTEM_PROMPT = """\
You are researching a company from the text of its own website page, to help a job candidate
understand what the company does before reaching out.

Rules, in order of importance:
1. Only report what the page text actually supports. Never invent customers, funding amounts,
   founders, or product claims not present in the text.
2. Every FACT must include an `evidence` field that is a literal, verbatim quote copied from the
   page text -- not a paraphrase. If you cannot find a verbatim quote, do not report it as a fact.
3. INFERENCES are the only place you may synthesize or interpret rather than quote -- e.g.
   "this company likely serves enterprise customers, based on the pricing page mentioning
   'contact sales'". Always include a one-sentence `reasoning`. Never present an inference as a
   fact, and never invent a connection or claim that the text gives no basis for at all.
4. Categorize each fact/inference as one of: what_they_build, customers, problem, funding,
   founders, product_direction, launch, engineering_challenge, other.
5. It's fine to return few or no facts if the page text is thin (e.g. a login wall, a mostly
   marketing-copy landing page) -- do not pad with generic filler.
"""


class LLMCompanyResearcher:
    def research(self, page_text: str, provider: LLMProvider) -> LLMCompanyResearchData:
        return provider.structured_completion(
            system=SYSTEM_PROMPT,
            prompt=page_text,
            response_model=LLMCompanyResearchData,
            prompt_version=PROMPT_VERSION,
        )
