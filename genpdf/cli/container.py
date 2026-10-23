"""Composition root: the only place that knows which adapter implements each port."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from genpdf.application.build_content import BuildContent
from genpdf.application.build_deck import BuildDeck
from genpdf.application.build_document import BuildDocument
from genpdf.application.create_content import CreateContent
from genpdf.application.validate_content import ValidateContent
from genpdf.infrastructure.chrome_renderer import ChromeDeckRenderer
from genpdf.infrastructure.file_storage import LocalFileStorage
from genpdf.infrastructure.markdown_parser import MarkdownContentParser
from genpdf.infrastructure.pdf_inspector import PypdfInspector
from genpdf.infrastructure.templating import Presentation
from genpdf.infrastructure.weasyprint_renderer import WeasyPrintDocumentRenderer

PRESENTATION_DIR = Path(__file__).resolve().parent.parent / "presentation"


@dataclass(frozen=True, slots=True)
class Container:
    storage: LocalFileStorage
    presentation: Presentation
    build: BuildContent
    validate: ValidateContent
    create: CreateContent


def create_container() -> Container:
    storage = LocalFileStorage()
    presentation = Presentation(PRESENTATION_DIR)
    parser = MarkdownContentParser()
    inspector = PypdfInspector()
    themes, icons = presentation.themes(), presentation.icons()

    build_document = BuildDocument(WeasyPrintDocumentRenderer(presentation), storage, inspector)
    build_deck = BuildDeck(ChromeDeckRenderer(presentation), storage, inspector, themes, icons)
    return Container(
        storage=storage,
        presentation=presentation,
        build=BuildContent(parser, storage, build_document, build_deck),
        validate=ValidateContent(parser, storage, themes, icons),
        create=CreateContent(storage),
    )
