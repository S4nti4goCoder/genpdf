"""Metadata of a piece (what goes in the frontmatter) and its defaults."""

from __future__ import annotations

import datetime
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from genpdf.domain.errors import ContentError


class ContentType(StrEnum):
    """Kind of piece. StrEnum: an enum whose values behave like strings."""

    DOCUMENT = "document"
    DECK = "deck"


@dataclass(frozen=True, slots=True)
class Metadata:
    type: ContentType
    title: str
    subtitle: str = ""
    author: str = ""
    date: str = ""
    theme: str = "default"
    cover: bool = False
    toc: bool = False
    toc_depth: int = 2
    max_pages: int | None = None
    lang: str = "es"

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any], source: str) -> Metadata:
        """Build the metadata, validating required fields, types and key names."""
        _reject_unknown_keys(raw, source)
        return cls(
            type=_content_type(raw, source),
            title=_required_text(raw, "title", source),
            subtitle=_text(raw, "subtitle", source),
            author=_text(raw, "author", source),
            date=_date(raw, source),
            theme=_text(raw, "theme", source) or "default",
            cover=_flag(raw, "cover", source),
            toc=_flag(raw, "toc", source),
            toc_depth=_positive_int(raw, "tocDepth", source) or 2,
            max_pages=_positive_int(raw, "maxPages", source),
            lang=_text(raw, "lang", source) or "es",
        )


# Accepted frontmatter keys. A misspelled "maxpages" must not pass silently.
KNOWN_KEYS = frozenset(
    {"type", "title", "subtitle", "author", "date", "theme", "cover", "toc", "tocDepth",
     "maxPages", "lang"}
)


def _reject_unknown_keys(raw: Mapping[str, Any], source: str) -> None:
    unknown = sorted(set(raw) - KNOWN_KEYS)
    if unknown:
        valid = ", ".join(sorted(KNOWN_KEYS))
        raise ContentError(
            f"unknown frontmatter field(s): {', '.join(unknown)}. Valid fields: {valid}",
            source,
            1,
        )


def _content_type(raw: Mapping[str, Any], source: str) -> ContentType:
    value = _required_text(raw, "type", source)
    try:
        return ContentType(value)
    except ValueError:
        raise ContentError(f"type must be 'document' or 'deck', not '{value}'", source, 1) from None


def _required_text(raw: Mapping[str, Any], key: str, source: str) -> str:
    value = _text(raw, key, source)
    if not value:
        raise ContentError(f"missing required frontmatter field '{key}'", source, 1)
    return value


def _text(raw: Mapping[str, Any], key: str, source: str) -> str:
    value = raw.get(key)
    if value is None:
        return ""
    # YAML turns "2.1" into a number; for a subtitle that is still text.
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise ContentError(f"'{key}' must be text, not {_type_name(value)}", source, 1)
    return str(value).strip()


def _flag(raw: Mapping[str, Any], key: str, source: str) -> bool:
    value = raw.get(key, False)
    if not isinstance(value, bool):
        raise ContentError(f"'{key}' must be true or false, not '{value}'", source, 1)
    return value


def _positive_int(raw: Mapping[str, Any], key: str, source: str) -> int | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ContentError(f"'{key}' must be a whole number greater than 0, not '{value}'",
                           source, 1)
    return value


def _date(raw: Mapping[str, Any], source: str) -> str:
    value = raw.get("date")
    # YAML reads 2026-10-22 as a date object, not text. Store it as ISO text.
    if isinstance(value, datetime.date):
        return value.isoformat()
    return _text(raw, "date", source)


def _type_name(value: object) -> str:
    return {list: "a list", dict: "a mapping", bool: "a boolean"}.get(
        type(value), type(value).__name__
    )
