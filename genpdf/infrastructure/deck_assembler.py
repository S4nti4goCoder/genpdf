"""Deck body -> slides.

Rules (documented in content/templates/deck.md):
- A line with only `---` (outside code blocks) separates slides.
- <!-- slide: kind --> sets the slide kind. Without it: the first slide is a cover,
  the rest are bullets.
- A short paragraph right before the title (# or ##) is the kicker.
- cards: each ### starts a card. <!-- icon: name --> sets its icon.
- two-columns: <!-- column --> separates the columns.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from genpdf.domain.blocks import Block, Heading, Image, Inline, Paragraph
from genpdf.domain.errors import ContentError
from genpdf.domain.models import Section, Slide, SlideKind
from genpdf.infrastructure.markdown_blocks import Directive, Node, Slugger

type Reader = Callable[[str, int, Slugger], list[Node]]

_SEPARATOR = re.compile(r"^-{3,}\s*$")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_KNOWN_DIRECTIVES = frozenset({"slide", "icon", "column"})
_VALID_KINDS = ", ".join(kind.value for kind in SlideKind)


def assemble_deck(read: Reader, body: str, body_offset: int, source: str) -> tuple[Slide, ...]:
    slugger = Slugger()
    slides: list[Slide] = []
    for start, text in split_slides(body):
        nodes = read(text, body_offset + start, slugger)
        line = nodes[0].line if nodes else body_offset + start + 1
        slides.append(assemble_slide(nodes, len(slides) + 1, line, source))
    if not slides:
        raise ContentError("the deck has no slides", source, body_offset + 1)
    return tuple(slides)


def split_slides(body: str) -> list[tuple[int, str]]:
    """(first line index, text) of each slide. A --- inside a code block does not split."""
    chunks: list[tuple[int, str]] = []
    current: list[str] = []
    start = 0
    fence: str | None = None
    for index, line in enumerate(body.splitlines()):
        fence = _track_fence(line, fence)
        if fence is None and _SEPARATOR.match(line):
            chunks.append((start, "\n".join(current)))
            current, start = [], index + 1
            continue
        current.append(line)
    chunks.append((start, "\n".join(current)))
    return [(s, text) for s, text in chunks if text.strip()]


def _track_fence(line: str, fence: str | None) -> str | None:
    match = _FENCE.match(line)
    if match is None:
        return fence
    if fence is None:
        return match[1]
    closes = match[1].startswith(fence) and not line.strip().strip(fence[0])
    return None if closes else fence


# ── One slide ──────────────────────────────────────────────────────────────────


def assemble_slide(nodes: list[Node], number: int, line: int, source: str) -> Slide:
    _reject_unknown_directives(nodes, source)
    kind = _slide_kind(nodes, number, source)
    content = [n for n in nodes if not (isinstance(n, Directive) and n.name == "slide")]
    kicker, title, rest = _split_title(content)
    slide = Slide(kind, number, line, kicker, title, ())
    builder = _BUILDERS.get(kind, _plain)
    return builder(slide, rest, source)


def _reject_unknown_directives(nodes: list[Node], source: str) -> None:
    for node in nodes:
        if isinstance(node, Directive) and node.name not in _KNOWN_DIRECTIVES:
            raise ContentError(
                f"unknown directive '<!-- {node.name} -->'. In a deck the valid ones are: "
                "slide, icon, column",
                source,
                node.line,
            )


def _slide_kind(nodes: list[Node], number: int, source: str) -> SlideKind:
    declared = [n for n in nodes if isinstance(n, Directive) and n.name == "slide"]
    if not declared:
        return SlideKind.COVER if number == 1 else SlideKind.BULLETS
    if len(declared) > 1:
        raise ContentError(f"slide {number} declares its kind twice", source, declared[1].line)
    try:
        return SlideKind(declared[0].value)
    except ValueError:
        raise ContentError(
            f"unknown slide kind '{declared[0].value}'. Valid kinds: {_VALID_KINDS}",
            source,
            declared[0].line,
        ) from None


def _split_title(nodes: list[Node]) -> tuple[tuple[Inline, ...], tuple[Inline, ...], list[Node]]:
    """(kicker, title, rest). The title is the first # or ##; a lone paragraph before it
    is the kicker."""
    index = next((i for i, n in enumerate(nodes) if isinstance(n, Heading) and n.level <= 2),
                 None)
    if index is None:
        return (), (), nodes
    before = nodes[:index]
    title = nodes[index]
    assert isinstance(title, Heading)
    content_before = [n for n in before if not isinstance(n, Directive)]
    kicker: tuple[Inline, ...] = ()
    if len(content_before) == 1 and isinstance(content_before[0], Paragraph):
        kicker = content_before[0].children
        before = [n for n in before if isinstance(n, Directive)]
    return kicker, title.children, [*before, *nodes[index + 1:]]


# ── Builders per kind ──────────────────────────────────────────────────────────


def _plain(slide: Slide, rest: list[Node], source: str) -> Slide:
    return dataclasses.replace(slide, blocks=_only_blocks(rest))


def _cards(slide: Slide, rest: list[Node], source: str) -> Slide:
    intro, sections = _split_cards(rest)
    return dataclasses.replace(slide, blocks=intro, sections=sections)


def _columns(slide: Slide, rest: list[Node], source: str) -> Slide:
    groups: list[tuple[int, list[Node]]] = [(slide.line, [])]
    for node in rest:
        if isinstance(node, Directive) and node.name == "column":
            groups.append((node.line, []))
        else:
            groups[-1][1].append(node)
    sections = tuple(_column(line, nodes) for line, nodes in groups if _only_blocks(nodes))
    return dataclasses.replace(slide, sections=sections)


def _full_image(slide: Slide, rest: list[Node], source: str) -> Slide:
    image = next((n for n in rest if isinstance(n, Image)), None)
    if image is None:
        raise ContentError(
            f"slide {slide.number} is full-image but has no image. "
            "Add a line with only ![description](path.png)",
            source,
            slide.line,
        )
    others = [n for n in rest if n is not image]
    return dataclasses.replace(slide, image=image, blocks=_only_blocks(others))


_BUILDERS: dict[SlideKind, Callable[[Slide, list[Node], str], Slide]] = {
    SlideKind.CARDS: _cards,
    SlideKind.TWO_COLUMNS: _columns,
    SlideKind.FULL_IMAGE: _full_image,
}


@dataclass(slots=True)
class _SectionDraft:
    """Mutable while it is being filled; frozen into a Section at the end."""

    heading: tuple[Inline, ...]
    icon: str | None
    line: int
    blocks: list[Block] = field(default_factory=list)

    def freeze(self) -> Section:
        return Section(self.heading, self.icon, tuple(self.blocks), self.line)


def _split_cards(nodes: list[Node]) -> tuple[tuple[Block, ...], tuple[Section, ...]]:
    """(intro, cards). An icon right before a ### belongs to that card; otherwise to the
    card it sits in."""
    intro: list[Block] = []
    cards: list[_SectionDraft] = []
    pending_icon: str | None = None
    for index, node in enumerate(nodes):
        if isinstance(node, Directive):
            if node.name != "icon":
                continue
            following = nodes[index + 1] if index + 1 < len(nodes) else None
            if cards and not _is_card_heading(following):
                cards[-1].icon = node.value
            else:
                pending_icon = node.value
        elif _is_card_heading(node):
            assert isinstance(node, Heading)
            cards.append(_SectionDraft(node.children, pending_icon, node.line))
            pending_icon = None
        else:
            (cards[-1].blocks if cards else intro).append(node)
    return tuple(intro), tuple(card.freeze() for card in cards)


def _column(line: int, nodes: list[Node]) -> Section:
    blocks = list(_only_blocks(nodes))
    icon = next((n.value for n in nodes if isinstance(n, Directive) and n.name == "icon"), None)
    if blocks and _is_card_heading(blocks[0]):
        first = blocks.pop(0)
        assert isinstance(first, Heading)
        return Section(first.children, icon, tuple(blocks), first.line)
    return Section((), icon, tuple(blocks), line)


def _is_card_heading(node: Node | None) -> bool:
    return isinstance(node, Heading) and node.level == 3


def _only_blocks(nodes: list[Node]) -> tuple[Block, ...]:
    return tuple(n for n in nodes if not isinstance(n, Directive))
