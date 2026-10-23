from __future__ import annotations

from pathlib import Path

from genpdf.application.build_deck import BuildDeck
from genpdf.application.build_document import BuildDocument
from genpdf.application.guards import BuildResult
from genpdf.application.ports import ContentParser, FileStorage
from genpdf.domain.models import Deck, Document


class BuildContent:
    """Read a .md, find out whether it is a document or a deck, and hand it to the right build."""

    def __init__(
        self,
        parser: ContentParser,
        storage: FileStorage,
        build_document: BuildDocument,
        build_deck: BuildDeck,
    ) -> None:
        self._parser = parser
        self._storage = storage
        self._build_document = build_document
        self._build_deck = build_deck

    def execute(self, source: Path, output_dir: Path) -> BuildResult:
        content = self._parser.parse(self._storage.read_text(source), source.as_posix())
        output = output_dir / f"{source.stem}.pdf"
        match content:
            case Document():
                return self._build_document.execute(content, source.parent, output)
            case Deck():
                return self._build_deck.execute(content, source.parent, output)
