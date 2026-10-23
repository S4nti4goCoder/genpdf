from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PdfReport:
    """What a written PDF actually contains, read back from disk."""

    size_bytes: int
    is_pdf: bool
    pages: int
    page_sizes: tuple[tuple[float, float], ...]  # (width, height) in points, one per page


class PdfInspector(Protocol):
    def inspect(self, path: Path) -> PdfReport:
        """Re-open a PDF and report on it. Raises RenderError if it cannot be read."""
        ...
