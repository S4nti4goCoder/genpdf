"""PdfRenderer[Deck] adapter: HTML printed to PDF by Chrome headless."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path

from genpdf.domain.errors import RenderError
from genpdf.domain.models import Deck, Theme
from genpdf.infrastructure.templating import Presentation

CHROME_ENV = "CHROME_PATH"

# Time Chrome may wait for web fonts before printing (virtual time, not wall clock).
_FONT_BUDGET_MS = 15000
_TIMEOUT_S = 180


def chrome_candidates(environ: Mapping[str, str]) -> list[Path]:
    """Typical install paths. Edge is Chromium too and accepts the same flags."""
    local = Path(environ.get("LOCALAPPDATA", ""))
    return [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        local / "Google" / "Chrome" / "Application" / "chrome.exe",
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/usr/bin/google-chrome"),
        Path("/usr/bin/chromium"),
    ]


def find_chrome(environ: Mapping[str, str]) -> Path:
    override = environ.get(CHROME_ENV)
    if override:
        path = Path(override)
        if not path.is_file():
            raise RenderError(f"{CHROME_ENV} points to '{path}', which does not exist")
        return path
    for candidate in chrome_candidates(environ):
        if candidate.is_file():
            return candidate
    raise RenderError(
        f"Chrome was not found in the usual paths. Install it or set {CHROME_ENV} "
        "to the full path of chrome.exe"
    )


class ChromeDeckRenderer:
    def __init__(
        self, presentation: Presentation, environ: Mapping[str, str] | None = None
    ) -> None:
        self._presentation = presentation
        self._environ = environ if environ is not None else os.environ

    def render(self, content: Deck, theme: Theme, base_dir: Path) -> bytes:
        html = self._html(content, theme, base_dir)
        chrome = find_chrome(self._environ)
        with tempfile.TemporaryDirectory(prefix="genpdf-") as tmp:
            workdir = Path(tmp)
            page = workdir / "deck.html"
            page.write_text(html, encoding="utf-8")
            output = workdir / "deck.pdf"
            _run_chrome(chrome, page, output, workdir / "profile", content.source)
            if not output.is_file():
                raise RenderError("Chrome finished but did not write the PDF", content.source)
            return output.read_bytes()

    def _html(self, deck: Deck, theme: Theme, base_dir: Path) -> str:
        try:
            theme_css = self._presentation.theme(theme.name)
        except RenderError as error:
            raise RenderError(error.message, deck.source, 1) from None
        return self._presentation.environment.get_template("deck.html").render(
            deck=deck,
            meta=deck.metadata,
            css=self._presentation.style("deck"),
            theme_css=theme_css,
            icons=self._presentation.icon_markup(),
            base_href=base_dir.resolve().as_uri() + "/",
        )


def _run_chrome(chrome: Path, page: Path, output: Path, profile: Path, source: str) -> None:
    command = [
        str(chrome),
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={profile}",  # Own profile: does not clash with an open Chrome.
        f"--virtual-time-budget={_FONT_BUDGET_MS}",
        f"--print-to-pdf={output}",
        page.as_uri(),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=_TIMEOUT_S,
                                check=False)
    except subprocess.TimeoutExpired:
        raise RenderError(f"Chrome took more than {_TIMEOUT_S}s and was stopped", source) from None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        raise RenderError(f"Chrome exited with code {result.returncode}: {' | '.join(detail)}",
                          source)
