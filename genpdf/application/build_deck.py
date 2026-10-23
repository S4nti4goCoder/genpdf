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
from genpdf.application.ports import FileStorage, PdfInspector, PdfRenderer, PdfReport
from genpdf.domain.models import Deck, Theme
from genpdf.domain.rules import deck_blocks, unknown_names

# A 1280x720 px slide printed at 96 dpi is 960x540 pt: exact 16:9.
SLIDE_SIZE_PT = (960.0, 540.0)
SIZE_TOLERANCE_PT = 1.0


class BuildDeck:
    """Print a Deck, write it, and verify every page is a 16:9 slide."""

    def __init__(
        self,
        renderer: PdfRenderer[Deck],
        storage: FileStorage,
        inspector: PdfInspector,
        themes: frozenset[str],
        icons: frozenset[str],
    ) -> None:
        self._renderer = renderer
        self._storage = storage
        self._inspector = inspector
        self._themes = themes
        self._icons = icons

    def execute(self, deck: Deck, base_dir: Path, output: Path) -> BuildResult:
        raise_if_any([
            *unknown_names(deck, self._themes, self._icons),
            *missing_images(self._storage, deck_blocks(deck), base_dir, deck.source),
        ])
        data = self._renderer.render(deck, Theme(deck.metadata.theme), base_dir)
        ensure_pdf_bytes(data, deck.source)
        self._storage.write_bytes(output, data)

        report = self._inspector.inspect(output)
        ensure_written_pdf(report, deck.source)
        violations = [
            *page_limit(report, deck.metadata.max_pages, output),
            *wrong_slide_sizes(report, output),
        ]
        return BuildResult(deck.source, output, report.size_bytes, report.pages,
                           tuple(violations))


def wrong_slide_sizes(report: PdfReport, output: Path) -> list[str]:
    expected_w, expected_h = SLIDE_SIZE_PT
    return [
        f"{output}: page {number} measures {w:.0f}x{h:.0f} pt, expected 960x540"
        for number, (w, h) in enumerate(report.page_sizes, start=1)
        if abs(w - expected_w) > SIZE_TOLERANCE_PT or abs(h - expected_h) > SIZE_TOLERANCE_PT
    ]
