"""AGLC4 report series abbreviations and bracket-type lookup.

Data sourced from reference_data.py — the single source of truth.
"""

from __future__ import annotations

from enum import Enum

from citefix.rules.reference_data import (
    COURT_IDENTIFIERS,
    REPORT_SERIES,
    all_round_bracket_series,
    all_square_bracket_identifiers,
    get_bracket_type as _rd_get_bracket_type,
    is_medium_neutral as _rd_is_medium_neutral,
)


class BracketType(Enum):
    ROUND = "round"
    SQUARE = "square"


# Derive sets from reference_data dicts, adding backward-compat extras not yet in reference_data.
ROUND_BRACKET_SERIES: set[str] = all_round_bracket_series() | {
    # Entries from the original hardcoded set not yet in REPORT_SERIES
    "TasR",
    "SR (Qld)",
    "SR (WA)",
    "ICR",
    "Cr App R",
    "BCLC",
    "Lloyd's Rep",
    "ATPR",
    "EOC",
}

MEDIUM_NEUTRAL_IDENTIFIERS: set[str] = set(COURT_IDENTIFIERS.keys()) | {
    # Entries from the original hardcoded set not yet in COURT_IDENTIFIERS
    "FMCA",
    "NSWCATOD",
    "NSWCATAP",
    "QMC",
    "QCAT",
    "VCAT",
    "SACAT",
    "NZSupC",
    "AAT",
    "TASCC",
}

# Year-organised report series — square brackets for year, but NOT medium neutral
SQUARE_BRACKET_REPORT_SERIES: set[str] = {
    k for k, v in REPORT_SERIES.items() if v["brackets"] == "square"
} | {
    "QdR",  # Alternate spelling (no space) from original hardcoded set
}

SQUARE_BRACKET_SERIES: set[str] = MEDIUM_NEUTRAL_IDENTIFIERS | SQUARE_BRACKET_REPORT_SERIES

ALL_REPORT_SERIES: set[str] = ROUND_BRACKET_SERIES | SQUARE_BRACKET_SERIES


def get_bracket_type(report_series: str) -> BracketType | None:
    """Return the required bracket type for a given report series abbreviation."""
    result = _rd_get_bracket_type(report_series)
    if result == "round":
        return BracketType.ROUND
    if result == "square":
        return BracketType.SQUARE

    # Fall back to local sets for backward-compat extras
    if report_series in ROUND_BRACKET_SERIES:
        return BracketType.ROUND
    if report_series in SQUARE_BRACKET_SERIES:
        return BracketType.SQUARE
    return None


def is_medium_neutral(report_series: str) -> bool:
    """Check if a report series is a medium-neutral citation identifier.

    Medium neutral identifiers (HCA, NSWSC, FCA, etc.) are court-allocated
    unique identifiers. They use square brackets but are distinct from
    year-organised traditional report series (Qd R, FLC) which also use
    square brackets.
    """
    return report_series in MEDIUM_NEUTRAL_IDENTIFIERS
