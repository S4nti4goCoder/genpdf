"""Shared fixtures. pytest injects them into any test that names them as a parameter."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from genpdf.domain.models import Deck, Document
from genpdf.infrastructure.markdown_parser import MarkdownContentParser
from tests.helpers import with_frontmatter


@pytest.fixture
def parser() -> MarkdownContentParser:
    return MarkdownContentParser()


@pytest.fixture
def parse_doc(parser: MarkdownContentParser) -> Callable[..., Document]:
    """parse_doc(body, toc=True) -> Document, with a valid frontmatter around the body."""

    def parse(body: str, **fields: object) -> Document:
        content = parser.parse(with_frontmatter(body, type="document", **fields), "test.md")
        assert isinstance(content, Document)
        return content

    return parse


@pytest.fixture
def parse_deck(parser: MarkdownContentParser) -> Callable[..., Deck]:
    def parse(body: str, **fields: object) -> Deck:
        content = parser.parse(with_frontmatter(body, type="deck", **fields), "test.md")
        assert isinstance(content, Deck)
        return content

    return parse
