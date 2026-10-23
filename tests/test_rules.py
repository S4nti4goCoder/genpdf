"""Business rules: placeholders, heading jumps, toc, slide capacity, unknown names."""

from __future__ import annotations

from genpdf.domain.models import SlideKind
from genpdf.domain.rules import (
    CARD_BULLETS,
    SLIDE_CAPACITY,
    deck_issues,
    document_issues,
    heading_jumps,
    placeholder_words,
    slide_capacity,
    toc_needs_h1,
    unknown_names,
)

THEMES = frozenset({"default", "github"})
ICONS = frozenset({"folder", "cloud"})


def messages(issues):
    return [issue.message for issue in issues]


# ── Placeholder text ───────────────────────────────────────────────────────────


def test_placeholders_are_found_in_prose(parse_doc):
    doc = parse_doc("# TODO\n\nLorem Ipsum dolor\n\n| a |\n|---|\n| XXX |\n")
    found = messages(placeholder_words(doc.blocks, doc.source))
    assert found == ["placeholder text: 'TODO'", "placeholder text: 'lorem ipsum'",
                     "placeholder text: 'XXX'"]


def test_placeholders_inside_lists_and_quotes(parse_doc):
    doc = parse_doc("- uno\n  - TODO\n\n> XXX\n")
    assert len(placeholder_words(doc.blocks, doc.source)) == 2


def test_code_and_spanish_words_are_not_placeholders(parse_doc):
    body = "Todo el sistema funciona.\n\nUsa `TODO` en código.\n\n```\n# TODO: XXX\n```\n"
    doc = parse_doc(body)
    assert placeholder_words(doc.blocks, doc.source) == []


def test_placeholder_reports_its_line(parse_doc):
    doc = parse_doc("Bien\n\nTODO arreglar\n")
    assert [i.line for i in placeholder_words(doc.blocks, doc.source)] == [7]


# ── Headings and table of contents ─────────────────────────────────────────────


def test_heading_jump_is_reported(parse_doc):
    doc = parse_doc("# Uno\n\n### Tres\n")
    issues = heading_jumps(doc)
    assert messages(issues) == ["heading level jump: h3 after h1. Use h2 or add the missing level"]
    assert issues[0].line == 7


def test_going_back_up_is_fine(parse_doc):
    assert heading_jumps(parse_doc("# A\n\n## B\n\n### C\n\n# D\n\n## E\n")) == []


def test_document_may_start_at_h2(parse_doc):
    assert heading_jumps(parse_doc("## Sección\n\n### Sub\n")) == []


def test_document_starting_at_h3_is_a_jump(parse_doc):
    assert len(heading_jumps(parse_doc("### Sub\n"))) == 1


def test_toc_needs_an_h1(parse_doc):
    assert len(toc_needs_h1(parse_doc("## Solo h2\n", toc=True))) == 1
    assert toc_needs_h1(parse_doc("# Capítulo\n", toc=True)) == []
    assert toc_needs_h1(parse_doc("## Sin índice\n")) == []


def test_clean_document_has_no_issues(parse_doc):
    assert document_issues(parse_doc("# Uno\n\n## Dos\n\nTexto real.\n", toc=True)) == []


# ── Slides ─────────────────────────────────────────────────────────────────────


def bullets(count: int) -> str:
    return "".join(f"- punto {n}\n" for n in range(count))


def test_bullets_slide_at_capacity_is_fine(parse_deck):
    limit = SLIDE_CAPACITY[SlideKind.BULLETS]
    deck = parse_deck(f"<!-- slide: bullets -->\n## A\n\n{bullets(limit)}")
    assert slide_capacity(deck) == []


def test_bullets_slide_over_capacity(parse_deck):
    limit = SLIDE_CAPACITY[SlideKind.BULLETS]
    deck = parse_deck(f"<!-- slide: bullets -->\n## A\n\n{bullets(limit + 1)}")
    assert messages(slide_capacity(deck)) == [
        f"slide 1: {limit + 1} bullets, {limit} fit. Split it into two slides"
    ]


def test_nested_bullets_count(parse_deck):
    limit = SLIDE_CAPACITY[SlideKind.BULLETS]
    nested = "- padre\n" + "".join(f"  - hijo {n}\n" for n in range(limit))
    assert len(slide_capacity(parse_deck(f"<!-- slide: bullets -->\n## A\n\n{nested}"))) == 1


def test_too_many_cards_and_bullets_per_card(parse_deck):
    cards = "".join(f"### Card {n}\n{bullets(CARD_BULLETS + 1)}\n" for n in range(5))
    found = messages(slide_capacity(parse_deck(f"<!-- slide: cards -->\n## A\n\n{cards}")))
    assert found[0] == "slide 1: 5 cards, 4 fit"
    assert found.count(f"slide 1: a card has {CARD_BULLETS + 1} bullets, {CARD_BULLETS} fit") == 5


def test_column_over_capacity(parse_deck):
    limit = SLIDE_CAPACITY[SlideKind.TWO_COLUMNS]
    body = f"<!-- slide: two-columns -->\n## A\n\n{bullets(limit + 2)}\n<!-- column -->\n- b\n"
    assert len(slide_capacity(parse_deck(body))) == 1


def test_unknown_theme_and_icon(parse_deck):
    deck = parse_deck("<!-- slide: cards -->\n## A\n\n<!-- icon: rocket -->\n### X\n",
                      theme="neon")
    found = messages(unknown_names(deck, THEMES, ICONS))
    assert found[0].startswith("theme 'neon' does not exist. Available: default, github")
    assert found[1].startswith("icon 'rocket' does not exist. Available: cloud, folder")


def test_placeholders_in_deck_titles_and_cards(parse_deck):
    deck = parse_deck("TODO\n# Portada\n\n---\n<!-- slide: cards -->\n## A\n\n### XXX\n")
    assert len(deck_issues(deck, THEMES, ICONS)) == 2
