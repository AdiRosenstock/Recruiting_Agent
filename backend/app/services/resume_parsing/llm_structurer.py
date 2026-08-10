"""LLM-powered step: turn raw resume text into an `LLMExtractedCandidateData` claim set.

The prompt is versioned (`PROMPT_VERSION`) so stored data can always be traced back to the
exact instructions that produced it -- architectural principle #14.
"""

from app.schemas.llm_extraction import LLMExtractedCandidateData
from app.services.llm.base import LLMProvider

PROMPT_VERSION = "resume_structurer_v1"

SYSTEM_PROMPT = """\
You are extracting a structured candidate profile from the raw text of one resume.

Rules, in order of importance:
1. Extract ONLY what is stated in the resume text. Never invent employers, titles, dates,
   metrics, or skills that are not present in the text.
2. Every education, experience, and project entry MUST include an `evidence_snippet` that is a
   literal, verbatim quote copied from the resume text -- not a paraphrase. If you cannot find
   a verbatim quote supporting an entry, do not include that entry.
3. Every skill claim's `evidence` list MUST contain literal, verbatim quotes from the resume
   text that mention or clearly imply that skill. If you cannot find at least one verbatim
   quote, do not include the skill.
4. `strengths` and `gaps` are the only fields where you may synthesize a short summary rather
   than quote verbatim -- but base them only on what the resume actually shows. Do not assume
   the candidate has deep ML-research / model-training experience unless the resume explicitly
   describes it; applied software/data/AI-engineering experience is not the same claim.
5. Categorize each skill as one of: language, framework, database, ai, data, tool, domain.
6. Categorize each experience entry as one of: work, leadership, project.
7. Dates may be left as written in the resume (e.g. "June 2026", "Expected 2027") -- do not
   reformat or guess missing components.
"""


class LLMResumeStructurer:
    def structure(self, raw_text: str, provider: LLMProvider) -> LLMExtractedCandidateData:
        return provider.structured_completion(
            system=SYSTEM_PROMPT,
            prompt=raw_text,
            response_model=LLMExtractedCandidateData,
            prompt_version=PROMPT_VERSION,
        )
