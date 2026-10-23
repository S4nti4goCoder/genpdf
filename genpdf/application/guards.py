"""Checks shared by both build use cases: before printing and after writing the PDF."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from genpdf.application.ports import FileStorage, PdfReport
from genpdf.domain.blocks import Block
from genpdf.domain.errors import RenderError, ValidationError
from genpdf.domain.rules import Issue, image_sources, is_local


@dataclass(frozen=True, slots=True)
class BuildResult:
    """Outcome of building one piece. `violations` non-empty means the build failed a guard."""

    source: str
    output: Path
    size_bytes: int
    pages: int
    violations: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.violations


def missing_images(
    storage: FileStorage, blocks: tuple[Block, ...], base_dir: Path, source: str
) -> list[Issue]:
    return [
        Issue(source, line, f"image not found: {src} (looked in {base_dir / src})")
        for src, line in image_sources(blocks)
        if is_local(src) and not storage.exists(base_dir / src)
    ]


def raise_if_any(issues: list[Issue]) -> None:
    """Blocking rules: if any fails, the piece is not printed."""
    if issues:
        first = issues[0]
        extra = f" (and {len(issues) - 1} more; run 'check')" if len(issues) > 1 else ""
        raise ValidationError(first.message + extra, first.source, first.line)


def ensure_pdf_bytes(data: bytes, source: str) -> None:
    if not data:
        raise RenderError("the engine returned an empty PDF", source)
    if not data.startswith(b"%PDF"):
        raise RenderError("the engine output does not start with %PDF", source)


def ensure_written_pdf(report: PdfReport, source: str) -> None:
    if report.size_bytes == 0 or not report.is_pdf:
        raise RenderError("the PDF written to disk is empty or corrupt", source)


def page_limit(report: PdfReport, max_pages: int | None, output: Path) -> list[str]:
    """maxPages is optional. Only if it is declared and exceeded is it a violation."""
    if max_pages is None or report.pages <= max_pages:
        return []
    return [f"{output}: {report.pages} pages, maxPages is {max_pages}"]
