"""Deck body -> slides: separators, kinds, kicker, cards, columns."""

from __future__ import annotations

import pytest

from genpdf.domain.blocks import BulletList, CodeBlock, Paragraph, Quote, plain_text
from genpdf.domain.errors import ContentError
from genpdf.domain.models import SlideKind
from genpdf.infrastructure.deck_assembler import split_slides


def test_separator_splits_slides(parse_deck):
    deck = parse_deck("# Uno\n\n---\n\n## Dos\n\n---\n## Tres\n")
    assert [plain_text(s.title) for s in deck.slides] == ["Uno", "Dos", "Tres"]
    assert [s.number for s in deck.slides] == [1, 2, 3]


def test_separator_inside_code_does_not_split():
    chunks = split_slides("## A\n```yaml\n---\nkey: v\n```\n---\n## B\n")
    assert len(chunks) == 2
    assert "key: v" in chunks[0][1]


def test_separator_inside_tilde_fence_does_not_split():
    assert len(split_slides("~~~\n---\n~~~\n")) == 1


def test_empty_slides_are_dropped(parse_deck):
    assert len(parse_deck("# Uno\n\n---\n\n---\n\n## Dos\n").slides) == 2


def test_default_kinds(parse_deck):
    deck = parse_deck("# Portada\n\n---\n\n## Algo\n\n- a\n")
    assert [s.kind for s in deck.slides] == [SlideKind.COVER, SlideKind.BULLETS]


@pytest.mark.parametrize("kind", [k.value for k in SlideKind if k is not SlideKind.FULL_IMAGE])
def test_every_declared_kind(parse_deck, kind):
    deck = parse_deck(f"<!-- slide: {kind} -->\n## Título\n\nTexto\n")
    assert deck.slides[0].kind.value == kind


def test_unknown_kind_lists_the_valid_ones(parse_deck):
    with pytest.raises(ContentError, match=r"unknown slide kind 'grid'.*cover, cards") as error:
        parse_deck("<!-- slide: grid -->\n## A\n")
    assert error.value.line == 5


def test_kind_declared_twice(parse_deck):
    with pytest.raises(ContentError, match="declares its kind twice"):
        parse_deck("<!-- slide: cards -->\n<!-- slide: bullets -->\n## A\n")


def test_unknown_directive_is_reported(parse_deck):
    with pytest.raises(ContentError, match="unknown directive '<!-- icn -->'"):
        parse_deck("## A\n\n<!-- icn: folder -->\n")


def test_kicker_is_the_paragraph_before_the_title(parse_deck):
    slide = parse_deck("<!-- slide: bullets -->\nFundamentos\n## Qué es Git\n\n- a\n").slides[0]
    assert plain_text(slide.kicker) == "Fundamentos"
    assert plain_text(slide.title) == "Qué es Git"
    assert isinstance(slide.blocks[0], BulletList)


def test_slide_without_title(parse_deck):
    slide = parse_deck("<!-- slide: quote -->\n> Cita\n\nAutor\n").slides[0]
    assert slide.title == () and slide.kicker == ()
    assert isinstance(slide.blocks[0], Quote) and isinstance(slide.blocks[1], Paragraph)


def test_cards_with_icons_before_or_after_the_heading(parse_deck):
    body = (
        "<!-- slide: cards -->\n## Piezas\n\nIntro\n\n"
        "<!-- icon: folder -->\n### Repo\nTexto\n\n"
        "### Commit\n<!-- icon: git-commit -->\n- a\n\n"
        "### Sin icono\nNada\n"
    )
    slide = parse_deck(body).slides[0]
    assert [plain_text(b.children) for b in slide.blocks if isinstance(b, Paragraph)] == ["Intro"]
    assert [(plain_text(c.heading), c.icon) for c in slide.sections] == [
        ("Repo", "folder"), ("Commit", "git-commit"), ("Sin icono", None)
    ]
    assert isinstance(slide.sections[1].blocks[0], BulletList)


def test_two_columns(parse_deck):
    body = (
        "<!-- slide: two-columns -->\n## Git vs GitHub\n\n### Git\n- local\n\n"
        "<!-- column -->\n<!-- icon: cloud -->\n### GitHub\n```bash\ngit push\n```\n"
    )
    left, right = parse_deck(body).slides[0].sections
    assert plain_text(left.heading) == "Git" and left.icon is None
    assert plain_text(right.heading) == "GitHub" and right.icon == "cloud"
    assert isinstance(right.blocks[0], CodeBlock)


def test_full_image_needs_an_image(parse_deck):
    with pytest.raises(ContentError, match="full-image but has no image"):
        parse_deck("<!-- slide: full-image -->\n## Sin imagen\n")


def test_full_image(parse_deck):
    body = "<!-- slide: full-image -->\n## Ramas\n\n![Grafo](img/g.svg)\n\nPie\n"
    slide = parse_deck(body).slides[0]
    assert slide.image is not None and slide.image.src == "img/g.svg"
    assert [plain_text(b.children) for b in slide.blocks] == ["Pie"]


def test_slide_line_numbers(parse_deck):
    deck = parse_deck("# Uno\n\n---\n\n## Dos\n")
    assert [s.line for s in deck.slides] == [5, 9]


def test_deck_without_slides(parse_deck):
    with pytest.raises(ContentError, match="no slides"):
        parse_deck("\n\n")
