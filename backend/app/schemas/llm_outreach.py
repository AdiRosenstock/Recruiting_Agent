"""The schema an LLM is constrained to fill when drafting outreach. Free-text voice output (not
evidence-quoted like resume/research extraction) -- the trust boundary here is enforced
downstream by the deterministic banned-phrase filter in services/outreach/agent.py, not by
structural validation of this schema.
"""

from pydantic import BaseModel, Field


class LLMOutreachMessages(BaseModel):
    linkedin_full: str = Field(description="The full personalized LinkedIn message.")
    linkedin_connection: str = Field(
        description="A short connection-request note, at most ~300 characters (LinkedIn's limit)."
    )
    email: str = Field(description="An email version, including a subject line as the first line.")
    personalization_rationale: str = Field(
        description="1-2 sentences on why this specific personalization was chosen."
    )
