from __future__ import annotations

from pathlib import Path

from genpdf.application.guards import missing_images
from genpdf.application.ports import ContentParser, FileStorage
from genpdf.domain.errors import ContentError
from genpdf.domain.models import Deck, Document
from genpdf.domain.rules import Issue, deck_blocks, deck_issues, document_issues


class ValidateContent:
    """Run every rule against a .md without printing anything."""

    def __init__(
        self,
        parser: ContentParser,
        storage: FileStorage,
        themes: frozenset[str],
        icons: frozenset[str],
    ) -> None:
        self._parser = parser
        self._storage = storage
        self._themes = themes
        self._icons = icons

    def execute(self, source: Path) -> list[Issue]:
        name = source.as_posix()
        try:
            content = self._parser.parse(self._storage.read_text(source), name)
        except ContentError as error:
            # A file that cannot be parsed is one more issue, not the end of the check.
            return [Issue(name, error.line or 1, error.message)]

        match content:
            case Document():
                issues = document_issues(content)
                blocks = content.blocks
            case Deck():
                issues = deck_issues(content, self._themes, self._icons)
                blocks = deck_blocks(content)
        issues.extend(missing_images(self._storage, blocks, source.parent, name))
        return sorted(issues, key=lambda issue: issue.line)
