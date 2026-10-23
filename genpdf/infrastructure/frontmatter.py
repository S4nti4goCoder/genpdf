"""Split the YAML frontmatter from the Markdown body and read it with pyyaml."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from genpdf.domain.errors import ContentError

_FENCE = "---"


@dataclass(frozen=True, slots=True)
class SplitContent:
    fields: dict[str, Any]
    body: str
    body_offset: int  # Lines before the body, to report real line numbers.


def split_frontmatter(text: str, source: str) -> SplitContent:
    lines = text.lstrip("﻿").splitlines()
    if not lines or lines[0].strip() != _FENCE:
        raise ContentError(
            "the file must start with a frontmatter block between '---' lines "
            "(at least 'type' and 'title')",
            source,
            1,
        )
    end = _closing_fence(lines, source)
    fields = _load_yaml("\n".join(lines[1:end]), source)
    return SplitContent(fields, "\n".join(lines[end + 1:]), end + 1)


def _closing_fence(lines: list[str], source: str) -> int:
    for index in range(1, len(lines)):
        if lines[index].strip() == _FENCE:
            return index
    raise ContentError("the frontmatter is never closed: a '---' line is missing", source, 1)


def _load_yaml(text: str, source: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        line = mark.line + 2 if mark else 1  # +1 for 1-based, +1 for the opening '---'
        raise ContentError(f"invalid YAML in the frontmatter: {error}", source, line) from None
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ContentError("the frontmatter must be 'key: value' pairs", source, 2)
    return data
