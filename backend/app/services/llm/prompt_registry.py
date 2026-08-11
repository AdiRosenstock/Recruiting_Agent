"""Central index of every LLM prompt in the system: which module owns it, its current version,
and a changelog of what each version changed and why.

Prompts themselves stay inline in their owning module (`services/resume_parsing/
llm_structurer.py`, `services/research/llm_researcher.py`, `services/outreach/
llm_outreach_writer.py`) -- co-locating a prompt with its one caller and its `PROMPT_VERSION`
constant is more readable than indirecting everything through a shared file. This is instead the
one place you can see *all* of them, their current versions, and their history at a glance --
useful when auditing "what prompt actually produced this stored row" (every LLM-derived row
carries its `prompt_version`: `candidate_profiles`, `company_research`, `outreach_messages`).

`tests/unit/test_prompt_registry.py` asserts every module's `PROMPT_VERSION` matches what's
registered here, and that it's the last entry in that prompt's changelog -- so bumping a
version without adding a changelog entry (or forgetting to update this file at all) fails a
test instead of silently drifting.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptChangelogEntry:
    version: str
    summary: str


@dataclass(frozen=True)
class PromptInfo:
    slug: str
    module: str
    changelog: list[PromptChangelogEntry] = field(default_factory=list)

    @property
    def current_version(self) -> str:
        return self.changelog[-1].version


PROMPT_REGISTRY: dict[str, PromptInfo] = {
    "resume_structurer": PromptInfo(
        slug="resume_structurer",
        module="app.services.resume_parsing.llm_structurer",
        changelog=[
            PromptChangelogEntry(
                version="resume_structurer_v1",
                summary=(
                    "Initial version: extract a candidate's structured profile from raw resume "
                    "text, with every skill claim required to carry a verbatim evidence quote "
                    "so downstream verification (services/evidence.py) can confirm or demote "
                    "it. Instructed to never invent education/experience/skills not present in "
                    "the text."
                ),
            ),
        ],
    ),
    "company_researcher": PromptInfo(
        slug="company_researcher",
        module="app.services.research.llm_researcher",
        changelog=[
            PromptChangelogEntry(
                version="company_researcher_v1",
                summary=(
                    "Initial version: split a fetched company page into FACT (verbatim "
                    "evidence quote required) vs. INFERENCE (synthesis allowed, must include a "
                    "one-sentence reasoning). Instructed to return few or no facts rather than "
                    "pad with generic filler for a thin page."
                ),
            ),
        ],
    ),
    "outreach_writer": PromptInfo(
        slug="outreach_writer",
        module="app.services.outreach.llm_outreach_writer",
        changelog=[
            PromptChangelogEntry(
                version="outreach_writer_v1",
                summary=(
                    "Initial version: draft linkedin_full/linkedin_connection/email variants "
                    "from real assembled context (candidate, job, company, research, contact). "
                    "Explicit voice guidance (direct college senior, not a corporate "
                    "recruiter) and a banned-phrase list in the prompt itself, backstopped by "
                    "the deterministic filter in services/outreach/banned_phrases.py -- the "
                    "prompt is the first line of defense, the filter is the one that can't "
                    "silently stop working."
                ),
            ),
        ],
    ),
}
