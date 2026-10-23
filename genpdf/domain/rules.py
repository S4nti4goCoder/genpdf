"""Business rules. Pure functions: they take the model and return the problems found."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

from genpdf.domain.blocks import (
    Block,
    BulletList,
    Heading,
    Image,
    InlineImage,
    Paragraph,
    Table,
    prose_text,
    walk,
)
from genpdf.domain.models import Deck, Document, Slide, SlideKind


@dataclass(frozen=True, slots=True)
class Issue:
    """A problem found, with its location so it can be fixed right away."""

    source: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.source}:{self.line}: {self.message}"


# How many bullets or cards fit on a 1280x720 slide without overflowing.
# This is the only place these numbers live.
SLIDE_CAPACITY: dict[SlideKind, int] = {
    SlideKind.BULLETS: 6,
    SlideKind.CARDS: 4,
    SlideKind.TWO_COLUMNS: 6,
}
CARD_BULLETS = 3

# Uppercase "TODO"/"XXX" as whole words only: Spanish "todo" is a normal word.
_PLACEHOLDERS = (
    (re.compile(r"\blorem ipsum\b", re.IGNORECASE), "lorem ipsum"),
    (re.compile(r"\bTODO\b"), "TODO"),
    (re.compile(r"\bXXX\b"), "XXX"),
)

# ── Document rules ─────────────────────────────────────────────────────────────


def toc_needs_h1(document: Document) -> list[Issue]:
    """With toc: true the table of contents needs at least one chapter (level-1 heading)."""
    if not document.metadata.toc:
        return []
    if any(isinstance(b, Heading) and b.level == 1 for b in document.blocks):
        return []
    return [Issue(document.source, 1,
                  "toc: true needs at least one level-1 heading (# Title) to build the index")]


def heading_jumps(document: Document) -> list[Issue]:
    """A heading cannot skip levels: a ### right under a # leaves a gap."""
    issues: list[Issue] = []
    previous = 1  # The frontmatter title acts as an implicit level 1.
    for block in document.blocks:
        if not isinstance(block, Heading):
            continue
        if block.level > previous + 1:
            issues.append(Issue(
                document.source, block.line,
                f"heading level jump: h{block.level} after h{previous}. "
                f"Use h{previous + 1} or add the missing level",
            ))
        previous = block.level
    return issues


def document_issues(document: Document) -> list[Issue]:
    return [
        *toc_needs_h1(document),
        *heading_jumps(document),
        *placeholder_words(document.blocks, document.source),
    ]


# ── Deck rules ─────────────────────────────────────────────────────────────────


def slide_capacity(deck: Deck) -> list[Issue]:
    """No slide may hold more bullets or cards than fit."""
    issues: list[Issue] = []
    for slide in deck.slides:
        issues.extend(_slide_overflow(slide, deck.source))
    return issues


def _slide_overflow(slide: Slide, source: str) -> Iterator[Issue]:
    limit = SLIDE_CAPACITY.get(slide.kind)
    if limit is None:
        return
    if slide.kind is SlideKind.BULLETS:
        count = count_list_items(slide.blocks)
        if count > limit:
            yield Issue(source, slide.line, f"slide {slide.number}: {count} bullets, {limit} fit."
                        " Split it into two slides")
    elif slide.kind is SlideKind.CARDS:
        yield from _cards_overflow(slide, source, limit)
    else:
        for column in slide.sections:
            count = count_list_items(column.blocks)
            if count > limit:
                yield Issue(source, column.line, f"slide {slide.number}: a column has "
                            f"{count} bullets, {limit} fit")


def _cards_overflow(slide: Slide, source: str, limit: int) -> Iterator[Issue]:
    if len(slide.sections) > limit:
        yield Issue(source, slide.line, f"slide {slide.number}: {len(slide.sections)} cards, "
                    f"{limit} fit")
    for card in slide.sections:
        count = count_list_items(card.blocks)
        if count > CARD_BULLETS:
            yield Issue(source, card.line, f"slide {slide.number}: a card has {count} bullets, "
                        f"{CARD_BULLETS} fit")


def count_list_items(blocks: tuple[Block, ...]) -> int:
    return sum(len(b.items) for b in walk(blocks) if isinstance(b, BulletList))


def unknown_names(deck: Deck, themes: frozenset[str], icons: frozenset[str]) -> list[Issue]:
    """Themes and icons that do not exist in presentation/."""
    issues: list[Issue] = []
    if deck.metadata.theme not in themes:
        issues.append(Issue(deck.source, 1, f"theme '{deck.metadata.theme}' does not exist. "
                            f"Available: {', '.join(sorted(themes))}"))
    for slide in deck.slides:
        for section in slide.sections:
            if section.icon and section.icon not in icons:
                issues.append(Issue(deck.source, section.line, f"icon '{section.icon}' does not "
                                    f"exist. Available: {', '.join(sorted(icons))}"))
    return issues


def deck_blocks(deck: Deck) -> tuple[Block, ...]:
    """Every block of the deck, in order, for rules that do not care about slides."""
    blocks: list[Block] = []
    for slide in deck.slides:
        blocks.append(Paragraph(slide.kicker, slide.line))
        blocks.append(Paragraph(slide.title, slide.line))
        blocks.extend(slide.blocks)
        if slide.image:
            blocks.append(slide.image)
        for section in slide.sections:
            blocks.append(Paragraph(section.heading, section.line))
            blocks.extend(section.blocks)
    return tuple(blocks)


def deck_issues(deck: Deck, themes: frozenset[str], icons: frozenset[str]) -> list[Issue]:
    return [
        *slide_capacity(deck),
        *unknown_names(deck, themes, icons),
        *placeholder_words(deck_blocks(deck), deck.source),
    ]


# ── Shared rules ───────────────────────────────────────────────────────────────


def placeholder_words(blocks: tuple[Block, ...], source: str) -> list[Issue]:
    """Leftover filler text. Code is ignored: "TODO" can be legitimate there."""
    issues: list[Issue] = []
    for block, text in _prose(blocks):
        for pattern, label in _PLACEHOLDERS:
            if pattern.search(text):
                issues.append(Issue(source, block.line, f"placeholder text: '{label}'"))
    return issues


def _prose(blocks: tuple[Block, ...]) -> Iterator[tuple[Block, str]]:
    for block in walk(blocks):
        match block:
            case Heading(children=c) | Paragraph(children=c):
                yield block, "".join(prose_text(c))
            case Table():
                cells = [cell for row in (block.header, *block.rows) for cell in row]
                yield block, " ".join("".join(prose_text(cell.children)) for cell in cells)
                yield block, "".join(prose_text(block.caption))
            case Image(caption=caption, alt=alt):
                yield block, f"{alt} {caption}"


def image_sources(blocks: tuple[Block, ...]) -> Iterator[tuple[str, int]]:
    """Referenced image paths (block or inline), with their line."""
    for block in walk(blocks):
        if isinstance(block, Image):
            yield block.src, block.line
        elif isinstance(block, Paragraph | Heading):
            for node in block.children:
                if isinstance(node, InlineImage):
                    yield node.src, block.line


def is_local(src: str) -> bool:
    """Remote or embedded images cannot be checked on disk."""
    return not src.startswith(("http://", "https://", "data:", "file:"))
