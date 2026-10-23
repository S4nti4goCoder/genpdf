"""Frontmatter -> Metadata: required fields, wrong types, defaults."""

from __future__ import annotations

import datetime

import pytest

from genpdf.domain.errors import ContentError
from genpdf.domain.metadata import ContentType, Metadata


def build(**raw: object) -> Metadata:
    return Metadata.from_mapping(raw, "x.md")


def test_defaults_when_only_required_fields():
    meta = build(type="document", title="Manual")
    assert meta.type is ContentType.DOCUMENT
    assert (meta.subtitle, meta.author, meta.date) == ("", "", "")
    assert (meta.cover, meta.toc, meta.toc_depth) == (False, False, 2)
    assert meta.theme == "default"
    assert meta.lang == "es"
    assert meta.max_pages is None  # No page limit unless it is declared.


def test_all_fields():
    meta = build(type="deck", title="Charla", subtitle="v2", author="Ana", date="hoy",
                 theme="github", cover=True, toc=True, tocDepth=3, maxPages=10, lang="en")
    assert meta.type is ContentType.DECK
    assert (meta.theme, meta.toc_depth, meta.max_pages, meta.lang) == ("github", 3, 10, "en")


@pytest.mark.parametrize("missing", ["type", "title"])
def test_missing_required_field(missing):
    raw = {"type": "document", "title": "x"}
    del raw[missing]
    with pytest.raises(ContentError, match=f"missing required frontmatter field '{missing}'"):
        build(**raw)


def test_empty_title_counts_as_missing():
    with pytest.raises(ContentError, match="'title'"):
        build(type="document", title="   ")


def test_unknown_type():
    with pytest.raises(ContentError, match="'document' or 'deck'"):
        build(type="slides", title="x")


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("cover", "yes", "'cover' must be true or false"),
        ("toc", 1, "'toc' must be true or false"),
        ("maxPages", 0, "'maxPages' must be a whole number"),
        ("maxPages", "10", "'maxPages' must be a whole number"),
        ("maxPages", True, "'maxPages' must be a whole number"),
        ("tocDepth", -1, "'tocDepth' must be a whole number"),
        ("title", ["a", "b"], "'title' must be text, not a list"),
        ("author", {"name": "x"}, "'author' must be text, not a mapping"),
        ("theme", False, "'theme' must be text"),
    ],
)
def test_wrong_types(field, value, message):
    raw = {"type": "document", "title": "x", field: value}
    with pytest.raises(ContentError, match=message):
        build(**raw)


def test_misspelled_key_is_rejected_with_the_valid_list():
    with pytest.raises(ContentError, match=r"unknown frontmatter field.*maxpages.*maxPages"):
        build(type="document", title="x", maxpages=3)


def test_yaml_date_object_becomes_iso_text():
    assert build(type="document", title="x", date=datetime.date(2026, 10, 22)).date == "2026-10-22"


def test_numbers_are_accepted_as_text():
    assert build(type="document", title="x", subtitle=2.1).subtitle == "2.1"


def test_error_points_to_file_and_line():
    with pytest.raises(ContentError) as error:
        build(type="document")
    assert str(error.value).startswith("x.md:1: ")


def test_frontmatter_through_the_parser(parser):
    text = "---\ntype: document\ntitle: Manual\ndate: 2026-10-22\ntoc: true\n---\n# Uno\n"
    assert parser.parse(text, "x.md").metadata.date == "2026-10-22"
