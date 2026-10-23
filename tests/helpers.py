"""Test helpers: frontmatter builder and port implementations that are not mocks."""

from __future__ import annotations

from pathlib import Path


def with_frontmatter(body: str, **fields: object) -> str:
    fields.setdefault("title", "Prueba")
    lines = [f"{key}: {_yaml(value)}" for key, value in fields.items()]
    return "---\n" + "\n".join(lines) + "\n---\n" + body


def _yaml(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


class MemoryStorage:
    """In-memory FileStorage: a real implementation of the port, not a mock."""

    def __init__(self, files: dict[Path, str] | None = None) -> None:
        self.files: dict[Path, str | bytes] = dict(files or {})

    def read_text(self, path: Path) -> str:
        value = self.files[path]
        assert isinstance(value, str)
        return value

    def write_bytes(self, path: Path, data: bytes) -> None:
        self.files[path] = data

    def write_text(self, path: Path, text: str) -> None:
        self.files[path] = text

    def exists(self, path: Path) -> bool:
        return path in self.files

    def list_markdown(self, directory: Path) -> list[Path]:
        return sorted(p for p in self.files if p.parent == directory and p.suffix == ".md")
