from pathlib import Path
from typing import Protocol

from genpdf.domain.models import Theme


class PdfRenderer[T](Protocol):
    """Model + theme -> PDF bytes.

    It is generic: PdfRenderer[Document] prints documents and PdfRenderer[Deck] prints
    decks. A use case only knows this interface, never which engine is behind it.
    """

    def render(self, content: T, theme: Theme, base_dir: Path) -> bytes:
        """`base_dir` is where relative paths (images) are resolved from. Raises RenderError."""
        ...
