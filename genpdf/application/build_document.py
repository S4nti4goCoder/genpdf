from __future__ import annotations

from pathlib import Path

from genpdf.application.guards import (
    BuildResult,
    ensure_pdf_bytes,
    ensure_written_pdf,
    missing_images,
    page_limit,
    raise_if_any,
)
from genpdf.application.ports import FileStorage, PdfInspector, PdfRenderer
from genpdf.domain.models import Document, Theme
from genpdf.domain.rules import toc_needs_h1


class BuildDocument:
    """Print a Document, write it, and verify what was written."""

    def __init__(
        self,
        renderer: PdfRenderer[Document],
        storage: FileStorage,
        inspector: PdfInspector,
    ) -> None:
        self._renderer = renderer
        self._storage = storage
        self._inspector = inspector

    def execute(self, document: Document, base_dir: Path, output: Path) -> BuildResult:
        raise_if_any([
            *toc_needs_h1(document),
            *missing_images(self._storage, document.blocks, base_dir, document.source),
        ])
        data = self._renderer.render(document, Theme(document.metadata.theme), base_dir)
        ensure_pdf_bytes(data, document.source)
        self._storage.write_bytes(output, data)

        report = self._inspector.inspect(output)
        ensure_written_pdf(report, document.source)
        return BuildResult(
            source=document.source,
            output=output,
            size_bytes=report.size_bytes,
            pages=report.pages,
            violations=tuple(page_limit(report, document.metadata.max_pages, output)),
        )
