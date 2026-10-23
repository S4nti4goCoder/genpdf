from __future__ import annotations

import re
from pathlib import Path

from genpdf.application.ports import FileStorage
from genpdf.domain.errors import ValidationError

_VALID_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class CreateContent:
    """Create a new .md from a starter template. Never overwrites an existing file."""

    def __init__(self, storage: FileStorage) -> None:
        self._storage = storage

    def execute(self, name: str, starter: str, content_dir: Path) -> Path:
        if not _VALID_NAME.match(name):
            raise ValidationError(
                f"invalid name '{name}': use lowercase letters, digits and dashes (my-document)"
            )
        target = content_dir / f"{name}.md"
        if self._storage.exists(target):
            raise ValidationError("already exists; pick another name or delete it first",
                                  target.as_posix())
        title = name.replace("-", " ").capitalize()
        self._storage.write_text(target, starter.replace("{{title}}", title))
        return target
