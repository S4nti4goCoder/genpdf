"""PdfInspector adapter: re-opens the written PDF with pypdf to verify it."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from genpdf.application.ports import PdfReport
from genpdf.domain.errors import RenderError


class PypdfInspector:
    def inspect(self, path: Path) -> PdfReport:
        size = path.stat().st_size
        with path.open("rb") as handle:
            is_pdf = handle.read(4) == b"%PDF"
        if not is_pdf:
            return PdfReport(size, False, 0, ())
        try:
            reader = PdfReader(path)
            sizes = tuple(
                (float(page.mediabox.width), float(page.mediabox.height)) for page in reader.pages
            )
        except PdfReadError as error:
            raise RenderError(f"pypdf cannot read the PDF: {error}", str(path)) from None
        return PdfReport(size, True, len(sizes), sizes)
