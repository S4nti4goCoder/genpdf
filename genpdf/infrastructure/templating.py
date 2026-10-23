"""Jinja2 setup shared by both renderers, plus the catalogs of themes and icons."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup

from genpdf.domain.errors import RenderError


class Presentation:
    """Access to presentation/: templates, styles, themes and icons."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.environment = Environment(
            loader=FileSystemLoader(root / "templates"),
            autoescape=True,
            undefined=StrictUndefined,  # A typo in a template fails loudly, not silently.
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.environment.filters["css_string"] = css_string

    def style(self, name: str) -> str:
        return (self.root / "styles" / f"{name}.css").read_text(encoding="utf-8")

    def theme(self, name: str) -> str:
        path = self.root / "themes" / f"{name}.css"
        if not path.is_file():
            available = ", ".join(sorted(self.themes()))
            raise RenderError(f"theme '{name}' does not exist. Available: {available}")
        return path.read_text(encoding="utf-8")

    def themes(self) -> frozenset[str]:
        return frozenset(path.stem for path in (self.root / "themes").glob("*.css"))

    def icons(self) -> frozenset[str]:
        return frozenset(path.stem for path in (self.root / "icons").glob("*.svg"))

    def icon_markup(self) -> dict[str, Markup]:
        """Every icon's SVG, read once per render. Markup marks it as safe HTML."""
        return {
            path.stem: Markup(path.read_text(encoding="utf-8").strip())
            for path in (self.root / "icons").glob("*.svg")
        }

    def starter(self, name: str) -> str:
        return (self.root / "starters" / f"{name}.md").read_text(encoding="utf-8")


def css_string(value: str) -> Markup:
    """Escape text for a CSS string literal inside <style>: content: "...";

    Inside <style> HTML entities are not decoded, so HTML escaping would show "&#34;".
    CSS escapes are used instead, and "<" is escaped so the text cannot close the tag.
    """
    escaped = (
        value.replace("\\", "\\\\").replace('"', '\\"').replace("<", "\\3C ").replace("\n", " ")
    )
    return Markup(escaped)
