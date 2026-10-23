"""markdown-it inline tokens -> domain inline nodes (text, bold, link...)."""

from __future__ import annotations

from markdown_it.token import Token

from genpdf.domain.blocks import (
    Emphasis,
    Inline,
    InlineCode,
    InlineImage,
    LineBreak,
    Link,
    RawInline,
    Strike,
    Strong,
    Text,
    plain_text,
)


def convert_inline(tokens: list[Token]) -> tuple[Inline, ...]:
    """Inline tokens arrive flat (strong_open, text, strong_close); a stack nests them."""
    stack: list[list[Inline]] = [[]]
    openers: list[Token] = []
    for token in tokens:
        if token.nesting == 1:
            stack.append([])
            openers.append(token)
        elif token.nesting == -1:
            children = _merge_text(stack.pop())
            stack[-1].append(_wrap(openers.pop(), children))
        else:
            stack[-1].extend(_leaf(token))
    return _merge_text(stack[0])


def _leaf(token: Token) -> list[Inline]:
    match token.type:
        case "text":
            return [Text(token.content)] if token.content else []
        case "softbreak":
            return [Text(" ")]
        case "hardbreak":
            return [LineBreak()]
        case "code_inline":
            return [InlineCode(token.content)]
        case "html_inline":
            return [RawInline(token.content)]
        case "image":
            alt = plain_text(convert_inline(token.children or []))
            return [InlineImage(str(token.attrGet("src") or ""), alt)]
        case _:
            return [Text(token.content)] if token.content else []


def _wrap(opener: Token, children: tuple[Inline, ...]) -> Inline:
    match opener.type:
        case "strong_open":
            return Strong(children)
        case "em_open":
            return Emphasis(children)
        case "s_open":
            return Strike(children)
        case "link_open":
            return Link(str(opener.attrGet("href") or ""), children)
        case _:
            return Emphasis(children)


def _merge_text(nodes: list[Inline]) -> tuple[Inline, ...]:
    """markdown-it splits text at special characters; adjacent pieces are joined back."""
    merged: list[Inline] = []
    for node in nodes:
        if isinstance(node, Text) and merged and isinstance(merged[-1], Text):
            merged[-1] = Text(merged[-1].text + node.text)
        else:
            merged.append(node)
    return tuple(merged)
