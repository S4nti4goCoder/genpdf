"""FileStorage adapter over the local disk."""

from __future__ import annotations

from pathlib import Path

from genpdf.domain.errors import ContentError, RenderError


class LocalFileStorage:
    def read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise ContentError("file not found", str(path)) from None
        except UnicodeDecodeError:
            raise ContentError("the file is not UTF-8; save it as UTF-8", str(path)) from None

    def write_bytes(self, path: Path, data: bytes) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except PermissionError:
            raise RenderError(
                "cannot write the PDF: is it open in a viewer that locks it? Close it and retry",
                str(path),
            ) from None

    def write_text(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def exists(self, path: Path) -> bool:
        return path.is_file()

    def list_markdown(self, directory: Path) -> list[Path]:
        return sorted(directory.glob("*.md"))
