from typing import Protocol

from genpdf.domain.models import Content


class ContentParser(Protocol):
    """Markdown text with frontmatter -> domain model (Document or Deck)."""

    def parse(self, text: str, source: str) -> Content:
        """`source` is only used in error messages. Raises ContentError."""
        ...
