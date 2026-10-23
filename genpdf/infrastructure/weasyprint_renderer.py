"""PdfRenderer[Document] adapter: HTML + paged-media CSS printed by WeasyPrint."""

from __future__ import annotations

import os
from pathlib import Path
from types import ModuleType

from genpdf.domain.errors import RenderError
from genpdf.domain.models import Document, Theme
from genpdf.infrastructure.templating import Presentation

# Where the MSYS2 installer puts Pango on Windows (see README).
_DEFAULT_DLL_DIR = Path(r"C:\msys64\ucrt64\bin")
_DLL_ENV = "WEASYPRINT_DLL_DIRECTORIES"


class WeasyPrintDocumentRenderer:
    def __init__(self, presentation: Presentation) -> None:
        self._presentation = presentation

    def render(self, content: Document, theme: Theme, base_dir: Path) -> bytes:
        # Documents have a single look for now; `theme` only applies to decks.
        html = self._presentation.environment.get_template("document.html").render(
            document=content,
            meta=content.metadata,
            toc=content.toc_entries() if content.metadata.toc else (),
            css=self._presentation.style("document"),
        )
        return _print(html, base_dir, content.source)


def _print(html: str, base_dir: Path, source: str) -> bytes:
    weasyprint = _load_weasyprint(source)
    try:
        return weasyprint.HTML(string=html, base_url=str(base_dir)).write_pdf()
    except Exception as error:  # WeasyPrint raises many types; re-raised with context.
        raise RenderError(f"WeasyPrint failed: {error}", source) from error


def _load_weasyprint(source: str) -> ModuleType:
    """Import on demand, so `check`, `new` and the parser work even without Pango."""
    if _DLL_ENV not in os.environ and _DEFAULT_DLL_DIR.is_dir():
        os.environ[_DLL_ENV] = str(_DEFAULT_DLL_DIR)
    try:
        import weasyprint
    except OSError as error:
        raise RenderError(
            f"WeasyPrint cannot load Pango ({error}). Install it with MSYS2 as the README "
            f"explains, or point {_DLL_ENV} to the folder that has libgobject-2.0-0.dll",
            source,
        ) from None
    return weasyprint
