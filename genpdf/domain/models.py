"""The printable pieces: Document (WeasyPrint) and Deck (Chrome)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from genpdf.domain.blocks import Block, Heading, Image, Inline
from genpdf.domain.metadata import Metadata


@dataclass(frozen=True, slots=True)
class Theme:
    """Visual identity. Just the name: which CSS file implements it is an outer concern."""

    name: str


@dataclass(frozen=True, slots=True)
class TocEntry:
    level: int
    children: tuple[Inline, ...]
    anchor: str


@dataclass(frozen=True, slots=True)
class Document:
    metadata: Metadata
    blocks: tuple[Block, ...]
    source: str

    def toc_entries(self) -> tuple[TocEntry, ...]:
        """Headings that go into the table of contents: top-level ones up to toc_depth."""
        depth = self.metadata.toc_depth
        return tuple(
            TocEntry(block.level, block.children, block.anchor)
            for block in self.blocks
            if isinstance(block, Heading) and block.level <= depth
        )


class SlideKind(StrEnum):
    COVER = "cover"
    CARDS = "cards"
    BULLETS = "bullets"
    TWO_COLUMNS = "two-columns"
    QUOTE = "quote"
    FULL_IMAGE = "full-image"
    CLOSING = "closing"


@dataclass(frozen=True, slots=True)
class Section:
    """A card (cards slide) or a column (two-columns slide)."""

    heading: tuple[Inline, ...]
    icon: str | None
    blocks: tuple[Block, ...]
    line: int


@dataclass(frozen=True, slots=True)
class Slide:
    kind: SlideKind
    number: int
    line: int
    kicker: tuple[Inline, ...]
    title: tuple[Inline, ...]
    blocks: tuple[Block, ...]
    sections: tuple[Section, ...] = ()
    image: Image | None = None


@dataclass(frozen=True, slots=True)
class Deck:
    metadata: Metadata
    slides: tuple[Slide, ...]
    source: str


type Content = Document | Deck
