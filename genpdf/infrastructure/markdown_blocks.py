"""markdown-it-py tokens -> domain blocks, in a single pass over the token list.

markdown-it produces a flat list of tokens (paragraph_open, inline, paragraph_close...).
TokenReader walks it once, left to right, building the nested block tree.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

from genpdf.domain.blocks import (
    Block,
    BulletList,
    CodeBlock,
    Heading,
    HorizontalRule,
    Image,
    Inline,
    InlineImage,
    ListItem,
    Paragraph,
    Quote,
    RawBlock,
    Table,
    TableCell,
    Text,
    plain_text,
)
from genpdf.infrastructure.markdown_inline import convert_inline


def create_markdown() -> MarkdownIt:
    """CommonMark + tables + strikethrough, with raw HTML allowed (the escape hatch)."""
    return MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])


@dataclass(frozen=True, slots=True)
class Directive:
    """An HTML comment like <!-- slide: cards -->. Not content: it steers the parser."""

    name: str
    value: str
    line: int


type Node = Block | Directive

_DIRECTIVE = re.compile(r"<!--\s*([a-z][a-z-]*)\s*(?::\s*(.*?))?\s*-->", re.DOTALL)
_ONLY_COMMENTS = re.compile(r"^(\s*<!--.*?-->\s*)+$", re.DOTALL)
_TABLE_CAPTION = re.compile(r"^\s*Tabla:\s*")


class Slugger:
    """Unique, readable anchors for headings: "Instalación" -> "instalacion"."""

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def slug(self, text: str) -> str:
        ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        base = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-") or "section"
        count = self._seen.get(base, 0) + 1
        self._seen[base] = count
        return base if count == 1 else f"{base}-{count}"


class TokenReader:
    def __init__(self, tokens: list[Token], line_offset: int, slugger: Slugger) -> None:
        self._tokens = tokens
        self._pos = 0
        self._offset = line_offset
        self._slugger = slugger
        self._handlers: dict[str, Callable[[Token], list[Node]]] = {
            "heading_open": self._heading,
            "paragraph_open": self._paragraph,
            "bullet_list_open": self._list,
            "ordered_list_open": self._list,
            "blockquote_open": self._quote,
            "fence": self._code,
            "code_block": self._code,
            "hr": self._rule,
            "html_block": self._html,
            "table_open": self._table,
        }

    def read(self) -> list[Node]:
        return self._until(None)

    # ── Traversal ──────────────────────────────────────────────────────────────

    def _until(self, closing: str | None) -> list[Node]:
        nodes: list[Node] = []
        while self._pos < len(self._tokens):
            token = self._tokens[self._pos]
            if token.type == closing:
                self._pos += 1
                return nodes
            handler = self._handlers.get(token.type)
            if handler is None:
                self._pos += 1  # Tokens without content of their own (closings, etc.).
                continue
            nodes.extend(handler(token))
        return nodes

    def _blocks_until(self, closing: str) -> tuple[Block, ...]:
        """Nested content (lists, quotes) has no directives: they only make sense on top."""
        return tuple(n for n in self._until(closing) if not isinstance(n, Directive))

    def _line(self, token: Token) -> int:
        return (token.map[0] if token.map else 0) + self._offset + 1

    def _inline_at(self, index: int) -> tuple[Inline, ...]:
        return convert_inline(self._tokens[index].children or [])

    # ── Handlers: each one consumes its tokens and returns the nodes built ─────

    def _heading(self, token: Token) -> list[Node]:
        children = self._inline_at(self._pos + 1)
        self._pos += 3  # heading_open, inline, heading_close
        anchor = self._slugger.slug(plain_text(children))
        return [Heading(int(token.tag[1]), children, anchor, self._line(token))]

    def _paragraph(self, token: Token) -> list[Node]:
        children = self._inline_at(self._pos + 1)
        self._pos += 3  # paragraph_open, inline, paragraph_close
        title = _lone_image_title(self._tokens[self._pos - 2])
        if title is not None and isinstance(children[0], InlineImage):
            image = children[0]
            return [Image(image.src, image.alt, title or image.alt, self._line(token))]
        return [Paragraph(children, self._line(token))]

    def _list(self, token: Token) -> list[Node]:
        self._pos += 1
        closing = token.type.replace("_open", "_close")
        items: list[ListItem] = []
        while self._tokens[self._pos].type != closing:
            self._pos += 1  # list_item_open
            items.append(ListItem(self._blocks_until("list_item_close")))
        self._pos += 1
        start = int(token.attrGet("start") or 1)
        ordered = token.type == "ordered_list_open"
        return [BulletList(tuple(items), ordered, start, self._line(token))]

    def _quote(self, token: Token) -> list[Node]:
        self._pos += 1
        return [Quote(self._blocks_until("blockquote_close"), self._line(token))]

    def _code(self, token: Token) -> list[Node]:
        self._pos += 1
        language = token.info.strip().split(" ")[0] if token.info else ""
        return [CodeBlock(token.content.rstrip("\n"), language, self._line(token))]

    def _rule(self, token: Token) -> list[Node]:
        self._pos += 1
        return [HorizontalRule(self._line(token))]

    def _html(self, token: Token) -> list[Node]:
        self._pos += 1
        if not _ONLY_COMMENTS.match(token.content):
            return [RawBlock(token.content, self._line(token))]
        return [
            Directive(match[1], (match[2] or "").strip(), self._line(token))
            for match in _DIRECTIVE.finditer(token.content)
        ]

    def _table(self, token: Token) -> list[Node]:
        line = self._line(token)
        header: tuple[TableCell, ...] = ()
        rows: list[tuple[TableCell, ...]] = []
        row: list[TableCell] = []
        self._pos += 1
        while self._tokens[self._pos].type != "table_close":
            current = self._tokens[self._pos]
            if current.type in ("th_open", "td_open"):
                row.append(TableCell(self._inline_at(self._pos + 1), _align(current)))
                self._pos += 2
            elif current.type == "tr_close":
                header, rows = (header, [*rows, tuple(row)]) if header else (tuple(row), rows)
                row = []
            self._pos += 1
        self._pos += 1
        return [Table(header, tuple(rows), (), line)]


def attach_table_captions(nodes: list[Node]) -> list[Node]:
    """A paragraph "Tabla: ..." right before a table becomes that table's caption."""
    result: list[Node] = []
    for node in nodes:
        previous = result[-1] if result else None
        if isinstance(node, Table) and isinstance(previous, Paragraph):
            caption = _caption_from(previous)
            if caption is not None:
                result[-1] = Table(node.header, node.rows, caption, node.line)
                continue
        result.append(node)
    return result


def _caption_from(paragraph: Paragraph) -> tuple[Inline, ...] | None:
    first = paragraph.children[0] if paragraph.children else None
    if not isinstance(first, Text) or not _TABLE_CAPTION.match(first.text):
        return None
    rest = _TABLE_CAPTION.sub("", first.text, count=1)
    return (Text(rest), *paragraph.children[1:]) if rest else paragraph.children[1:]


def _lone_image_title(inline: Token) -> str | None:
    """If the paragraph is just one image, its title ("" if none). Otherwise None."""
    children = [
        c for c in inline.children or [] if not (c.type == "text" and not c.content.strip())
    ]
    if len(children) == 1 and children[0].type == "image":
        return str(children[0].attrGet("title") or "")
    return None


def _align(cell: Token) -> str | None:
    style = str(cell.attrGet("style") or "")
    return style.removeprefix("text-align:") or None
