"""Use cases that do not print: validation and file creation, over in-memory storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from genpdf.application.create_content import CreateContent
from genpdf.application.validate_content import ValidateContent
from genpdf.domain.errors import ValidationError
from genpdf.infrastructure.markdown_parser import MarkdownContentParser
from tests.helpers import MemoryStorage, with_frontmatter

CONTENT = Path("content")


def validator(files: dict[Path, str]) -> ValidateContent:
    return ValidateContent(MarkdownContentParser(), MemoryStorage(files),
                           frozenset({"default"}), frozenset({"folder"}))


def test_missing_image_is_reported_relative_to_the_md():
    source = CONTENT / "doc.md"
    files = {
        source: with_frontmatter("![a](img/ok.png)\n\n![b](img/falta.png)\n", type="document"),
        CONTENT / "img" / "ok.png": "",
    }
    issues = validator(files).execute(source)
    assert [i.message.split(" (")[0] for i in issues] == ["image not found: img/falta.png"]
    assert issues[0].line == 7


def test_remote_images_are_not_checked():
    source = CONTENT / "doc.md"
    files = {source: with_frontmatter("![a](https://x.dev/a.png)\n", type="document")}
    assert validator(files).execute(source) == []


def test_unparseable_file_is_one_issue_not_a_crash():
    source = CONTENT / "roto.md"
    issues = validator({source: "sin frontmatter"}).execute(source)
    assert len(issues) == 1 and "frontmatter" in issues[0].message


def test_issues_are_sorted_by_line():
    source = CONTENT / "doc.md"
    body = "TODO\n\n# A\n\n### salto\n\n![x](no.png)\n"
    issues = validator({source: with_frontmatter(body, type="document")}).execute(source)
    assert [i.line for i in issues] == sorted(i.line for i in issues)
    assert len(issues) == 3


def test_deck_rules_run_for_decks():
    source = CONTENT / "deck.md"
    body = "<!-- slide: cards -->\n## A\n\n<!-- icon: nope -->\n### X\n"
    issues = validator({source: with_frontmatter(body, type="deck")}).execute(source)
    assert [i.message.split(".")[0] for i in issues] == ["icon 'nope' does not exist"]


def test_create_content_fills_the_title():
    storage = MemoryStorage()
    target = CreateContent(storage).execute("mi-manual", "title: {{title}}", CONTENT)
    assert target == CONTENT / "mi-manual.md"
    assert storage.files[target] == "title: Mi manual"


def test_create_content_never_overwrites():
    storage = MemoryStorage({CONTENT / "x.md": "original"})
    with pytest.raises(ValidationError, match="already exists"):
        CreateContent(storage).execute("x", "nuevo", CONTENT)
    assert storage.files[CONTENT / "x.md"] == "original"


@pytest.mark.parametrize("name", ["Mi Doc", "mi_doc", "../fuera", "-x", ""])
def test_create_content_rejects_bad_names(name):
    with pytest.raises(ValidationError, match="invalid name"):
        CreateContent(MemoryStorage()).execute(name, "", CONTENT)
