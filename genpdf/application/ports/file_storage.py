from pathlib import Path
from typing import Protocol


class FileStorage(Protocol):
    """Reads and writes files."""

    def read_text(self, path: Path) -> str: ...

    def write_bytes(self, path: Path, data: bytes) -> None: ...

    def write_text(self, path: Path, text: str) -> None: ...

    def exists(self, path: Path) -> bool: ...

    def list_markdown(self, directory: Path) -> list[Path]:
        """The .md files of a directory, sorted by name."""
        ...
