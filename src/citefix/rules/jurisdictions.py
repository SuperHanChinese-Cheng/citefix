"""AGLC4 jurisdiction abbreviation mappings.

Data sourced from reference_data.py — the single source of truth.
"""

from __future__ import annotations

from citefix.rules.reference_data import (
    JURISDICTIONS as _RD_JURISDICTIONS,
    JURISDICTION_FULL_TO_ABBR as _RD_FULL_TO_ABBR,
    PINPOINT_CORRECTIONS as _RD_PINPOINT_CORRECTIONS,
)

JURISDICTION_ABBREVIATIONS: dict[str, str] = dict(_RD_JURISDICTIONS)
VALID_JURISDICTIONS: set[str] = set(JURISDICTION_ABBREVIATIONS.keys())

# Build reverse lookup with common variants
FULL_NAME_TO_ABBREVIATION: dict[str, str] = dict(_RD_FULL_TO_ABBR)
# Add extra variants not in reference_data
FULL_NAME_TO_ABBREVIATION.setdefault("Commonwealth of Australia", "Cth")

ALL_JURISDICTION_NAMES: set[str] = VALID_JURISDICTIONS | set(FULL_NAME_TO_ABBREVIATION.keys())

# Source pinpoint corrections from reference_data, add extras for backward compat
SECTION_ABBREVIATIONS: dict[str, str] = dict(_RD_PINPOINT_CORRECTIONS)
# Ensure all existing entries remain (backward compatibility with original hardcoded dict)
SECTION_ABBREVIATIONS.setdefault("SECTION", "s")
SECTION_ABBREVIATIONS.setdefault("Sec", "s")
SECTION_ABBREVIATIONS.setdefault("Sec.", "s")
SECTION_ABBREVIATIONS.setdefault("Ch", "ch")
# Original jurisdictions.py used "cll" for clauses (not "cls" from reference_data).
# Override to preserve backward compat.
SECTION_ABBREVIATIONS["clauses"] = "cll"
SECTION_ABBREVIATIONS["Clauses"] = "cll"

PINPOINT_WORDS_TO_REMOVE: set[str] = {
    "p.", "pp.", "p", "pp",
    "at", "page", "pages",
    "para", "paragraph", "paras", "paragraphs",
}
