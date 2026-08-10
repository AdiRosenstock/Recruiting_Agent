"""Where uploaded resume files physically live.

Kept behind a small Protocol so swapping local disk for S3 (or anything else) later only means
writing a new class here -- nothing else in the app should know or care where bytes are stored.
"""

import uuid
from pathlib import Path
from typing import Protocol


class ResumeStorage(Protocol):
    def save(self, *, candidate_id: uuid.UUID, filename: str, content: bytes) -> str:
        """Persist the file; return a path/key that can be used to retrieve it later."""
        ...


class LocalFileStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def save(self, *, candidate_id: uuid.UUID, filename: str, content: bytes) -> str:
        candidate_dir = self._base_dir / str(candidate_id)
        candidate_dir.mkdir(parents=True, exist_ok=True)
        # Prefix with a random token so re-uploading a same-named file never clobbers history.
        safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
        path = candidate_dir / safe_name
        path.write_bytes(content)
        return str(path)
