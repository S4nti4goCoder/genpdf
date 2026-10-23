"""Content blocks: the tree produced from Markdown and painted by the templates.

Two levels:
- Inline: what lives inside a paragraph (text, bold, link, inline code...).
- Block: what takes its own vertical space (heading, paragraph, table, image...).

Every class declares `kind`, a short name the templates use to decide how to paint it.
`ClassVar` marks a class attribute, not a constructor field.
`line` is the .md line where the block starts, used in error messages.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar

# ── Inline ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Text:
    kind: ClassVar[str] = "text"
    text: str


@dataclass(frozen=True, slots=True)
class Strong:
    kind: ClassVar[str] = "strong"
    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class Emphasis:
    kind: ClassVar[str] = "emphasis"
    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class Strike:
    kind: ClassVar[str] = "strike"
    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class InlineCode:
    kind: ClassVar[str] = "code"
    text: str


@dataclass(frozen=True, slots=True)
class Link:
    kind: ClassVar[str] = "link"
    href: str
    children: tuple[Inline, ...]


@dataclass(frozen=True, slots=True)
class InlineImage:
    kind: ClassVar[str] = "image"
    src: str
    alt: str


@dataclass(frozen=True, slots=True)
class LineBreak:
    kind: ClassVar[str] = "break"


@dataclass(frozen=True, slots=True)
class RawInline:
    """Hand-written HTML inside a paragraph. Passed through to the PDF untouched."""

    kind: ClassVar[str] = "raw"
    html: str


type Inline = (
    Text | Strong | Emphasis | Strike | InlineCode | Link | InlineImage | LineBreak | RawInline
)

# ── Blocks ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Heading:
    kind: ClassVar[str] = "heading"
    level: int
    children: tuple[Inline, ...]
    anchor: str
    line: int


@dataclass(frozen=True, slots=True)
class Paragraph:
    kind: ClassVar[str] = "paragraph"
    children: tuple[Inline, ...]
    line: int


@dataclass(frozen=True, slots=True)
class ListItem:
    blocks: tuple[Block, ...]


@dataclass(frozen=True, slots=True)
class BulletList:
    """Bulleted list (ordered=False) or numbered list (ordered=True)."""

    kind: ClassVar[str] = "list"
    items: tuple[ListItem, ...]
    ordered: bool
    start: int
    line: int


@dataclass(frozen=True, slots=True)
class TableCell:
    children: tuple[Inline, ...]
    align: str | None


@dataclass(frozen=True, slots=True)
class Table:
    kind: ClassVar[str] = "table"
    header: tuple[TableCell, ...]
    rows: tuple[tuple[TableCell, ...], ...]
    caption: tuple[Inline, ...]
    line: int


@dataclass(frozen=True, slots=True)
class CodeBlock:
    kind: ClassVar[str] = "codeblock"
    code: str
    language: str
    line: int


@dataclass(frozen=True, slots=True)
class Image:
    """An image alone in its paragraph. Painted as a numbered figure with a caption."""

    kind: ClassVar[str] = "figure"
    src: str
    alt: str
    caption: str
    line: int


@dataclass(frozen=True, slots=True)
class Quote:
    kind: ClassVar[str] = "quote"
    blocks: tuple[Block, ...]
    line: int


@dataclass(frozen=True, slots=True)
class HorizontalRule:
    kind: ClassVar[str] = "rule"
    line: int


@dataclass(frozen=True, slots=True)
class PageBreak:
    """Forced page break, written as <!-- pagebreak --> in a document."""

    kind: ClassVar[str] = "pagebreak"
    line: int


@dataclass(frozen=True, slots=True)
class RawBlock:
    """A hand-written HTML block. The escape hatch for when Markdown is not enough."""

    kind: ClassVar[str] = "raw"
    html: str
    line: int


type Block = (
    Heading
    | Paragraph
    | BulletList
    | Table
    | CodeBlock
    | Image
    | Quote
    | HorizontalRule
    | PageBreak
    | RawBlock
)

# ── Traversals ─────────────────────────────────────────────────────────────────


def walk(blocks: tuple[Block, ...]) -> Iterator[Block]:
    """Yield every block once, including those nested in lists and quotes."""
    for block in blocks:
        yield block
        if isinstance(block, BulletList):
            for item in block.items:
                yield from walk(item.blocks)
        elif isinstance(block, Quote):
            yield from walk(block.blocks)


def plain_text(nodes: tuple[Inline, ...]) -> str:
    """Plain text of an inline sequence, formatting stripped. Inline code is included."""
    return "".join(_plain(node) for node in nodes)


def _plain(node: Inline) -> str:
    match node:
        case Text(text=text) | InlineCode(text=text):
            return text
        case Strong(children=c) | Emphasis(children=c) | Strike(children=c) | Link(children=c):
            return plain_text(c)
        case InlineImage(alt=alt):
            return alt
        case LineBreak():
            return " "
        case _:
            return ""


def prose_text(nodes: tuple[Inline, ...]) -> Iterator[str]:
    """Text pieces written by the author, without inline code or raw HTML."""
    for node in nodes:
        match node:
            case Text(text=text):
                yield text
            case Strong(children=c) | Emphasis(children=c) | Strike(children=c) | Link(children=c):
                yield from prose_text(c)
            case InlineImage(alt=alt):
                yield alt
