"""Configurable fit-score weights. Defaults match the original spec; a profile's
`config.weights` (see schemas/search_profile.py) overrides individual components -- e.g. the
`new_grad_2027` profile sets `stage: 0.0` and redistributes it into `role`/`experience`, done
entirely in that profile's seeded config, not in code (see scripts/seed_profiles.py).
"""

from typing import Any

from pydantic import BaseModel

# Bumped whenever the *meaning* of a component changes (not for config overrides, which are
# already captured separately) -- stored on every fit_scores row so re-scoring history stays
# traceable if the scoring logic itself evolves later.
WEIGHTS_VERSION = "v1"


class FitScoreWeights(BaseModel):
    technical: float = 0.25
    role: float = 0.20
    ai_data: float = 0.15
    experience: float = 0.15
    stage: float = 0.10
    location: float = 0.10
    domain: float = 0.05

    @classmethod
    def from_profile_config(cls, overrides: dict[str, Any]) -> "FitScoreWeights":
        return cls(**{**cls().model_dump(), **overrides})

    @property
    def total(self) -> float:
        """Not assumed to be 1.0 -- the scorer normalizes by this rather than trusting profile
        configs to always sum exactly to 1, since weights are hand-edited JSONB."""
        return sum(self.model_dump().values())
