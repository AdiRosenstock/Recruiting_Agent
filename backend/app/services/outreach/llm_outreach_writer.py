"""LLM-powered step: draft outreach messages from assembled context (candidate, job, company
research, contact). Versioned prompt, same pattern as the resume structurer / company researcher.
"""

from app.schemas.llm_outreach import LLMOutreachMessages
from app.services.llm.base import LLMProvider

PROMPT_VERSION = "outreach_writer_v1"

SYSTEM_PROMPT = """\
You are drafting outreach messages from a Northwestern senior (Adi Rosenstock) to someone at an
early-stage startup he wants to work for, based on his real background and genuine research
about the company, both provided to you below.

Voice: write like a smart, direct college senior emailing a founder or engineer he's genuinely
interested in -- not a corporate recruiter, not a cover letter, not a LinkedIn InMail template.
Concrete and specific beats polished and generic.

Never use: "significant ownership", "synergy", "revolutionary", "I am extremely passionate",
"I am thrilled to apply", or any other startup-buzzword-y, obviously-AI-written phrasing.

Do NOT mechanically reuse the wording below -- it's a shape, not a template to fill in. Vary it
based on what's actually interesting about this specific company:
  - Open with a specific, genuine observation about what the company is building.
  - One or two lines on the most relevant parts of his background (Bloomberg data
    engineering/agentic AI work is usually the strongest thing to lead with).
  - One personalized paragraph connecting his background/interests to this particular company --
    use the provided research/personal-connection notes only if they are genuinely relevant; do
    not force a connection that isn't there.
  - Close with genuine interest in a conversation, not "thrilled to apply."

Only use information provided to you below. Never invent facts about the candidate or the
company that aren't given to you.

Generate three variants sharing the same personalization:
  - linkedin_full: the full message.
  - linkedin_connection: a short connection-request note, at most ~300 characters.
  - email: an email version, with a subject line as its first line.
Also give a 1-2 sentence personalization_rationale explaining what you chose to lead with and why.
"""


class LLMOutreachWriter:
    def write(self, context_prompt: str, provider: LLMProvider) -> LLMOutreachMessages:
        return provider.structured_completion(
            system=SYSTEM_PROMPT,
            prompt=context_prompt,
            response_model=LLMOutreachMessages,
            prompt_version=PROMPT_VERSION,
        )
