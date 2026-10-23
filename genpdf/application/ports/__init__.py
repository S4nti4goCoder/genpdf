"""Ports: the interfaces the use cases depend on. Adapters in infrastructure/ implement them.

A Protocol works like a TypeScript interface: any class with matching methods satisfies
it, without inheriting from it.
"""

from genpdf.application.ports.content_parser import ContentParser
from genpdf.application.ports.file_storage import FileStorage
from genpdf.application.ports.pdf_inspector import PdfInspector, PdfReport
from genpdf.application.ports.pdf_renderer import PdfRenderer

__all__ = ["ContentParser", "FileStorage", "PdfInspector", "PdfRenderer", "PdfReport"]
