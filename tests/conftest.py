"""Shared test fixtures for CiteFix."""

from __future__ import annotations

import pytest

from citefix.models import Footnote, FootnoteRun


def make_footnote(
    index: int,
    text: str,
    *,
    italic_ranges: list[tuple[int, int]] | None = None,
) -> Footnote:
    """Create a Footnote from plain text, optionally marking italic ranges.

    Args:
        index: Footnote number.
        text: Full footnote text.
        italic_ranges: List of (start, end) char positions that should be italic.
    """
    if italic_ranges is None:
        return Footnote(index=index, runs=[FootnoteRun(text=text)])

    runs: list[FootnoteRun] = []
    sorted_ranges = sorted(italic_ranges)
    pos = 0
    for start, end in sorted_ranges:
        if pos < start:
            runs.append(FootnoteRun(text=text[pos:start], italic=False))
        runs.append(FootnoteRun(text=text[start:end], italic=True))
        pos = end
    if pos < len(text):
        runs.append(FootnoteRun(text=text[pos:], italic=False))

    return Footnote(index=index, runs=runs)
