"""ContentParser adapter: Markdown with frontmatter -> Document or Deck."""

from __future__ import annotations

from genpdf.domain.blocks import Block, PageBreak
from genpdf.domain.metadata import ContentType, Metadata
from genpdf.domain.models import Content, Deck, Document
from genpdf.infrastructure.deck_assembler import assemble_deck
from genpdf.infrastructure.frontmatter import split_frontmatter
from genpdf.infrastructure.markdown_blocks import (
    Directive,
    Node,
    Slugger,
    TokenReader,
    attach_table_captions,
    create_markdown,
)


class MarkdownContentParser:
    def __init__(self) -> None:
        self._markdown = create_markdown()

    def parse(self, text: str, source: str) -> Content:
        split = split_frontmatter(text, source)
        metadata = Metadata.from_mapping(split.fields, source)
        if metadata.type is ContentType.DECK:
            return Deck(metadata, assemble_deck(self._read, split.body, split.body_offset,
                                                source), source)
        nodes = self._read(split.body, split.body_offset, Slugger())
        return Document(metadata, _document_blocks(nodes), source)

    def _read(self, markdown: str, line_offset: int, slugger: Slugger) -> list[Node]:
        tokens = self._markdown.parse(markdown)
        return attach_table_captions(TokenReader(tokens, line_offset, slugger).read())


def _document_blocks(nodes: list[Node]) -> tuple[Block, ...]:
    """In a document the only directive is <!-- pagebreak -->; other comments are notes."""
    blocks: list[Block] = []
    for node in nodes:
        if isinstance(node, Directive):
            if node.name == "pagebreak":
                blocks.append(PageBreak(node.line))
            continue
        blocks.append(node)
    return tuple(blocks)
