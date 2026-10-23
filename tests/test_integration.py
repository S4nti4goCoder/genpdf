"""Real PDFs, real engines. No mocks: these prove the renderers actually work.

They are slower (a few seconds). The deck test is skipped if Chrome is not installed.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from pypdf import PdfReader

from genpdf.cli.container import create_container
from genpdf.domain.errors import RenderError, ValidationError
from genpdf.infrastructure.chrome_renderer import find_chrome
from tests.helpers import with_frontmatter


def chrome_available() -> bool:
    try:
        find_chrome(os.environ)
    except RenderError:
        return False
    return True


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def long_table(rows: int) -> str:
    lines = "".join(f"| {n} | Fila {n} | `v{n}` |\n" for n in range(rows))
    return f"Tabla: Una tabla que se parte\n\n| N | Texto | Código |\n|---|---|---|\n{lines}"


DOCUMENT_BODY = (
    "# Capítulo uno\n\nTexto con **negrita**.\n\n## Sección\n\n- a\n  - b\n\n"
    "```python\nprint('hola')\n```\n\n"
    "# Capítulo dos\n\n" + long_table(90) + "\n\n# Capítulo tres\n\n> Fin.\n"
)


def test_document_with_cover_toc_and_split_table(tmp_path):
    source = write(tmp_path / "manual.md", with_frontmatter(
        DOCUMENT_BODY, type="document", cover=True, toc=True, author="Ana", date="2026-10-22"))
    result = create_container().build.execute(source, tmp_path / "out")

    assert result.ok
    reader = PdfReader(result.output)
    assert result.pages == len(reader.pages) >= 6  # cover + toc + 3 chapters, table spans pages
    assert result.output.read_bytes().startswith(b"%PDF")

    cover, toc = (reader.pages[i].extract_text() for i in (0, 1))
    assert "Página" not in cover  # The cover carries no page number.
    assert f"Página 2 de {result.pages}" in toc
    # The index points to the page each chapter really starts on. Layout mode keeps the
    # "title .... page" line together.
    toc_layout = reader.pages[1].extract_text(extraction_mode="layout")
    listed = int(re.search(r"Capítulo dos[\s.]*(\d+)", toc_layout)[1])
    body_pages = enumerate(reader.pages[2:], start=3)  # After the cover and the index.
    starts = next(i for i, p in body_pages if "Capítulo dos" in p.extract_text())
    assert listed == starts
    # The table header repeats on the page after the break.
    assert "N Texto Código" in reader.pages[starts].extract_text()


def test_short_document_without_cover(tmp_path):
    source = write(tmp_path / "nota.md", with_frontmatter("## Resumen\n\nUna página.\n",
                                                          type="document"))
    result = create_container().build.execute(source, tmp_path)
    assert result.ok and result.pages == 1


def test_ordered_list_keeps_its_start_number(tmp_path):
    source = write(tmp_path / "lista.md", with_frontmatter("5. quinto\n6. sexto\n",
                                                           type="document"))
    result = create_container().build.execute(source, tmp_path)
    text = PdfReader(result.output).pages[0].extract_text(extraction_mode="layout")
    assert re.search(r"5\.\s+quinto", text) and re.search(r"6\.\s+sexto", text)


def test_max_pages_is_a_violation_only_when_declared(tmp_path):
    body = "# Uno\n\nA\n\n# Dos\n\nB\n\n# Tres\n\nC\n"
    limited = write(tmp_path / "limitado.md", with_frontmatter(body, type="document",
                                                               maxPages=2))
    result = create_container().build.execute(limited, tmp_path / "out")
    assert result.pages == 3
    assert result.violations == (f"{result.output}: 3 pages, maxPages is 2",)


def test_toc_without_h1_is_blocked_before_printing(tmp_path):
    source = write(tmp_path / "x.md", with_frontmatter("## Solo h2\n", type="document",
                                                       toc=True))
    with pytest.raises(ValidationError, match="level-1 heading"):
        create_container().build.execute(source, tmp_path / "out")
    assert not (tmp_path / "out" / "x.pdf").exists()


@pytest.mark.skipif(not chrome_available(), reason="Chrome is not installed")
def test_deck_pages_are_16_9(tmp_path):
    (tmp_path / "img").mkdir()
    write(tmp_path / "img" / "g.svg",
          '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200">'
          '<rect width="400" height="200" fill="#58a6ff"/></svg>')
    body = (
        "# Portada\n\n---\n<!-- slide: cards -->\n## Cartas\n\n<!-- icon: folder -->\n"
        "### Uno\nTexto\n\n### Dos\nTexto\n\n---\n<!-- slide: full-image -->\n## Imagen\n\n"
        "![Grafo](img/g.svg)\n\n---\n<!-- slide: closing -->\n# Gracias\n"
    )
    source = write(tmp_path / "charla.md", with_frontmatter(body, type="deck", theme="github"))
    result = create_container().build.execute(source, tmp_path / "out")

    assert result.ok, result.violations
    reader = PdfReader(result.output)
    assert len(reader.pages) == 4
    for page in reader.pages:
        assert (round(float(page.mediabox.width)), round(float(page.mediabox.height))) == (960,
                                                                                          540)
    assert "Cartas" in reader.pages[1].extract_text()  # Text stays selectable.
