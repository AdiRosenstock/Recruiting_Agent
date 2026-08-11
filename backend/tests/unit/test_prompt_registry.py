"""Keeps app/services/llm/prompt_registry.py honest: every prompt-owning module's PROMPT_VERSION
constant has to match a registered entry, and that entry has to be the *last* changelog entry --
so a version bump with no corresponding changelog update (or a registry that's drifted out of
sync with the code entirely) fails here instead of silently going unnoticed.
"""

from app.services.llm.prompt_registry import PROMPT_REGISTRY
from app.services.outreach.llm_outreach_writer import PROMPT_VERSION as OUTREACH_WRITER_VERSION
from app.services.research.llm_researcher import PROMPT_VERSION as COMPANY_RESEARCHER_VERSION
from app.services.resume_parsing.llm_structurer import PROMPT_VERSION as RESUME_STRUCTURER_VERSION

_ACTUAL_VERSIONS = {
    "resume_structurer": RESUME_STRUCTURER_VERSION,
    "company_researcher": COMPANY_RESEARCHER_VERSION,
    "outreach_writer": OUTREACH_WRITER_VERSION,
}


def test_every_prompt_module_is_registered() -> None:
    assert set(_ACTUAL_VERSIONS) == set(PROMPT_REGISTRY)


def test_registered_current_version_matches_the_module_constant() -> None:
    for slug, actual_version in _ACTUAL_VERSIONS.items():
        info = PROMPT_REGISTRY[slug]
        assert info.current_version == actual_version, (
            f"{slug}: PROMPT_VERSION in {info.module} is {actual_version!r}, but "
            f"prompt_registry.py's changelog's last entry is {info.current_version!r} -- "
            "add a PromptChangelogEntry for the new version."
        )


def test_every_prompt_has_at_least_one_changelog_entry() -> None:
    for slug, info in PROMPT_REGISTRY.items():
        assert info.changelog, f"{slug} has no changelog entries"


def test_changelog_versions_are_unique() -> None:
    for slug, info in PROMPT_REGISTRY.items():
        versions = [entry.version for entry in info.changelog]
        assert len(versions) == len(set(versions)), f"{slug} has duplicate changelog versions"
