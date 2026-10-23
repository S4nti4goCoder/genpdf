"""Markdown -> domain blocks: every block type and the awkward cases."""

from __future__ import annotations

import pytest

from genpdf.domain.blocks import (
    BulletList,
    CodeBlock,
    Emphasis,
    Heading,
    HorizontalRule,
    Image,
    InlineCode,
    InlineImage,
    LineBreak,
    Link,
    PageBreak,
    Paragraph,
    Quote,
    RawBlock,
    RawInline,
    Strike,
    Strong,
    Table,
    Text,
    plain_text,
)
from genpdf.domain.errors import ContentError


def only(blocks, kind):
    found = [b for b in blocks if isinstance(b, kind)]
    assert len(found) == 1, f"expected one {kind.__name__}, got {found}"
    return found[0]


# ── Headings ───────────────────────────────────────────────────────────────────


def test_headings_h1_to_h4_with_levels_and_anchors(parse_doc):
    doc = parse_doc("# Uno\n\n## Dos\n\n### Tres\n\n#### Cuatro\n")
    headings = [b for b in doc.blocks if isinstance(b, Heading)]
    assert [h.level for h in headings] == [1, 2, 3, 4]
    assert [h.anchor for h in headings] == ["uno", "dos", "tres", "cuatro"]


def test_anchors_drop_accents_and_stay_unique(parse_doc):
    doc = parse_doc("# Instalación\n\n# Instalación\n\n# ¿Qué es?\n")
    anchors = [b.anchor for b in doc.blocks if isinstance(b, Heading)]
    assert anchors == ["instalacion", "instalacion-2", "que-es"]


def test_line_numbers_count_the_frontmatter(parse_doc):
    # Frontmatter: '---', 'type', 'title', '---' -> the body starts at line 5.
    doc = parse_doc("# Uno\n\nTexto\n")
    assert doc.blocks[0].line == 5
    assert doc.blocks[1].line == 7


# ── Inline ─────────────────────────────────────────────────────────────────────


def test_inline_formatting(parse_doc):
    doc = parse_doc("Hola **negrita** *cursiva* ~~tachado~~ `código` [enlace](https://x.dev)\n")
    children = only(doc.blocks, Paragraph).children
    kinds = [type(c) for c in children if not isinstance(c, Text)]
    assert kinds == [Strong, Emphasis, Strike, InlineCode, Link]
    link = next(c for c in children if isinstance(c, Link))
    assert link.href == "https://x.dev"
    assert plain_text(link.children) == "enlace"


def test_nested_inline_formatting(parse_doc):
    doc = parse_doc("**negrita con *cursiva* dentro**\n")
    strong = only(doc.blocks, Paragraph).children[0]
    assert isinstance(strong, Strong)
    assert any(isinstance(c, Emphasis) for c in strong.children)


def test_hard_break_and_inline_html(parse_doc):
    doc = parse_doc("línea uno  \nlínea dos <kbd>Ctrl</kbd>\n")
    children = only(doc.blocks, Paragraph).children
    assert any(isinstance(c, LineBreak) for c in children)
    assert RawInline("<kbd>") in children


def test_adjacent_text_pieces_are_merged(parse_doc):
    doc = parse_doc("a_b_c [no es enlace]\n")
    assert only(doc.blocks, Paragraph).children == (Text("a_b_c [no es enlace]"),)


# ── Lists ──────────────────────────────────────────────────────────────────────


def test_bullet_and_ordered_lists(parse_doc):
    doc = parse_doc("- a\n- b\n\n3. tres\n4. cuatro\n")
    bullets, numbered = [b for b in doc.blocks if isinstance(b, BulletList)]
    assert not bullets.ordered and len(bullets.items) == 2
    assert numbered.ordered and numbered.start == 3


def test_nested_list(parse_doc):
    doc = parse_doc("- padre\n  - hijo\n    - nieto\n- otro\n")
    outer = only(doc.blocks, BulletList)
    assert len(outer.items) == 2
    child_list = outer.items[0].blocks[1]
    assert isinstance(child_list, BulletList)
    grandchild = child_list.items[0].blocks[1]
    assert isinstance(grandchild, BulletList)
    assert plain_text(grandchild.items[0].blocks[0].children) == "nieto"


# ── Tables ─────────────────────────────────────────────────────────────────────


def test_table_with_empty_cells_and_alignment(parse_doc):
    doc = parse_doc("| a | b | c |\n|:--|:-:|--:|\n|   | 2 |   |\n| x |   | z |\n")
    table = only(doc.blocks, Table)
    assert [c.align for c in table.header] == ["left", "center", "right"]
    assert len(table.rows) == 2
    assert table.rows[0][0].children == ()
    assert table.rows[1][1].children == ()
    assert plain_text(table.rows[1][2].children) == "z"


def test_table_without_body_rows(parse_doc):
    table = only(parse_doc("| a | b |\n|---|---|\n").blocks, Table)
    assert len(table.header) == 2 and table.rows == ()


def test_table_caption_from_previous_paragraph(parse_doc):
    doc = parse_doc("Tabla: Códigos *HTTP*\n\n| a |\n|---|\n| 1 |\n")
    table = only(doc.blocks, Table)
    assert plain_text(table.caption) == "Códigos HTTP"
    assert not any(isinstance(b, Paragraph) for b in doc.blocks)


def test_ordinary_paragraph_before_table_is_kept(parse_doc):
    doc = parse_doc("Un párrafo normal.\n\n| a |\n|---|\n| 1 |\n")
    assert only(doc.blocks, Table).caption == ()
    assert only(doc.blocks, Paragraph)


# ── Code ───────────────────────────────────────────────────────────────────────


def test_fenced_code_with_language(parse_doc):
    code = only(parse_doc("```python\nprint('hola')\n```\n").blocks, CodeBlock)
    assert code.language == "python"
    assert code.code == "print('hola')"


def test_code_containing_backticks(parse_doc):
    body = "````markdown\nUsa ```js para abrir un bloque\n```\n````\n"
    code = only(parse_doc(body).blocks, CodeBlock)
    assert code.code == "Usa ```js para abrir un bloque\n```"


def test_inline_code_with_backticks_inside(parse_doc):
    children = only(parse_doc("Escribe `` `x` `` así\n").blocks, Paragraph).children
    assert InlineCode("`x`") in children


def test_code_keeps_markdown_untouched(parse_doc):
    code = only(parse_doc("```\n# no es título\n- ni lista\n```\n").blocks, CodeBlock)
    assert code.code == "# no es título\n- ni lista"
    assert code.language == ""


# ── Images, quotes, rules, raw HTML ────────────────────────────────────────────


def test_lone_image_becomes_figure_with_title_as_caption(parse_doc):
    image = only(parse_doc('![Texto alternativo](img/a.png "Pie de foto")\n').blocks, Image)
    assert (image.src, image.alt, image.caption) == ("img/a.png", "Texto alternativo",
                                                     "Pie de foto")


def test_image_without_title_uses_alt_as_caption(parse_doc):
    image = only(parse_doc("![Diagrama de flujo](img/a.png)\n").blocks, Image)
    assert image.caption == "Diagrama de flujo"


def test_image_inside_text_stays_inline(parse_doc):
    children = only(parse_doc("Mira ![icono](i.png) aquí\n").blocks, Paragraph).children
    assert InlineImage("i.png", "icono") in children


def test_quote_with_nested_blocks(parse_doc):
    quote = only(parse_doc("> Primera línea\n>\n> - punto\n").blocks, Quote)
    assert isinstance(quote.blocks[0], Paragraph)
    assert isinstance(quote.blocks[1], BulletList)


def test_horizontal_rule(parse_doc):
    assert only(parse_doc("Antes\n\n---\n\nDespués\n").blocks, HorizontalRule)


def test_raw_html_block_passes_through(parse_doc):
    raw = only(parse_doc('<div class="aviso">Hola</div>\n').blocks, RawBlock)
    assert raw.html.strip() == '<div class="aviso">Hola</div>'


def test_pagebreak_directive_and_plain_comments(parse_doc):
    doc = parse_doc("Uno\n\n<!-- pagebreak -->\n\n<!-- una nota -->\n\nDos\n")
    assert only(doc.blocks, PageBreak)
    assert not any(isinstance(b, RawBlock) for b in doc.blocks)


def test_empty_body_is_a_valid_document(parse_doc):
    assert parse_doc("").blocks == ()


# ── Frontmatter framing ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, message",
    [
        ("# Sin frontmatter\n", "must start with a frontmatter"),
        ("---\ntype: document\ntitle: x\n", "never closed"),
        ("---\ntype: [document\n---\n", "invalid YAML"),
        ("---\n- una\n- lista\n---\n", "key: value"),
    ],
)
def test_broken_frontmatter(parser, text, message):
    with pytest.raises(ContentError, match=message) as error:
        parser.parse(text, "x.md")
    assert error.value.source == "x.md"
