"""Project-specific exceptions.

All of them inherit from GenpdfError, so the CLI can catch them without catching
programming errors (a KeyError or TypeError still blows up as it should).
"""

from __future__ import annotations


class GenpdfError(Exception):
    """An error that knows where it happened: which file, which line, and what to do."""

    def __init__(self, message: str, source: str | None = None, line: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.source = source
        self.line = line

    def __str__(self) -> str:
        if self.source and self.line:
            return f"{self.source}:{self.line}: {self.message}"
        if self.source:
            return f"{self.source}: {self.message}"
        return self.message


class ContentError(GenpdfError):
    """The content (Markdown or frontmatter) is malformed."""


class RenderError(GenpdfError):
    """The print engine failed or produced an invalid PDF."""


class ValidationError(GenpdfError):
    """The content can be read but breaks a business rule."""
