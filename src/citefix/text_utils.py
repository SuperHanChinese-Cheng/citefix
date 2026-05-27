"""Shared text utilities — Unicode normalisation and helpers.

Extracted to its own module to avoid circular imports between classifier
and parsers (classifier imports parsers, parsers need normalize_text).
"""

from __future__ import annotations

import regex

# Zero-width characters to strip during normalization
_ZERO_WIDTH_CHARS = regex.compile(r"[​‌‍﻿]")


def normalize_text(text: str) -> str:
    """Normalize Unicode oddities in footnote text before classification.

    Handles common copy-paste artefacts from Word, web pages, and PDFs:
    - Non-breaking space (\\xa0) → regular space
    - Zero-width chars (ZWSP, ZWNJ, ZWJ, BOM) → removed
    - Fullwidth parentheses （）→ ()
    - Fullwidth comma ， → ,
    - Em-dash — → en-dash –
    - Collapses multiple consecutive spaces into a single space
    - Strips leading/trailing whitespace
    """
    # Replace non-breaking space with regular space
    text = text.replace("\xa0", " ")
    # Strip zero-width characters
    text = _ZERO_WIDTH_CHARS.sub("", text)
    # Replace fullwidth parens
    text = text.replace("（", "(").replace("）", ")")
    # Replace fullwidth comma
    text = text.replace("，", ",")
    # Replace em-dash with en-dash
    text = text.replace("—", "–")
    # Collapse multiple consecutive spaces into single space
    text = regex.sub(r" {2,}", " ", text)
    # Strip leading/trailing whitespace
    return text.strip()
