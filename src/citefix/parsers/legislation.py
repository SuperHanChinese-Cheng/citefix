"""Legislation citation parser (AGLC4 Part 3)."""

from __future__ import annotations

import regex

from citefix.text_utils import normalize_text
from citefix.models import FootnoteRun, ParseResult, SourceType
from citefix.parsers.base import BaseCitationParser
from citefix.rules.jurisdictions import (
    ALL_JURISDICTION_NAMES,
    FULL_NAME_TO_ABBREVIATION,
    SECTION_ABBREVIATIONS,
    VALID_JURISDICTIONS,
)

# Build jurisdiction patterns — longest first to prevent partial matches
_ABBREV_PATTERN = "|".join(sorted(VALID_JURISDICTIONS, key=len, reverse=True))
_FULL_NAME_PATTERN = "|".join(
    regex.escape(n) for n in sorted(FULL_NAME_TO_ABBREVIATION.keys(), key=len, reverse=True)
)
_ALL_JURIS_PATTERN = _FULL_NAME_PATTERN + "|" + _ABBREV_PATTERN

# Pinpoint type alternatives — longest first
# Pinpoint type alternatives — longest first within each group to prevent
# partial matches (e.g., "reg" matching before "regulation")
_PINPOINT_TYPE_PATTERN = (
    r"section|Section|sec\.?|ss|§|"
    r"Regulations|regulation|Regulation|regs|reg|"
    r"rules|Rules|rule|Rule|rr|r|"
    r"clauses|Clauses|clause|Clause|cll|cl|"
    r"schedule|Schedule|sch|"
    r"chapter|Chapter|Ch|"
    r"part|Part|pt|"
    r"division|Division|div|"
    r"paragraph|Paragraph|para|"
    r"s\.|s"
)

# Primary pattern: Title Year (Jurisdiction) pinpoint
# Now accepts: abbreviated OR full jurisdiction names, with brackets
LEGISLATION_PATTERN = regex.compile(
    r"""
    (?P<title>
        (?:[\w'''-]+\s+)*            # Title words (including lowercase like "of", "and")
        (?:Act|Ordinance|Regulation|Regulations|Rules?|Code|Law|Bill|Charter|Constitution|Statute|By-laws?)
    )
    \s+
    (?P<year>\d{4})
    \s*
    \((?P<jurisdiction>""" + _ALL_JURIS_PATTERN + r""")\)
    (?:
        \s*,?\s*                     # Optional comma (common error)
        (?P<pinpoint_type>""" + _PINPOINT_TYPE_PATTERN + r""")
        \s*                          # Space is optional (handles §14(1))
        (?P<pinpoint>[\d\w()–\-,.\s]+?)
    )?
    \s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Extended pattern: Title Year Jurisdiction (no brackets) pinpoint
# Handles: "Legal Profession Uniform General Rules 2015 NSW regulation 42."
LEGISLATION_BARE_JURIS_PATTERN = regex.compile(
    r"""
    (?P<title>
        (?:[\w'''-]+\s+)*
        (?:Act|Ordinance|Regulation|Regulations|Rules?|Code|Law|Bill|Charter|Constitution|Statute|By-laws?)
    )
    \s+
    (?P<year>\d{4})
    \s+
    (?P<jurisdiction>""" + _ABBREV_PATTERN + r""")  # Bare abbreviation without brackets
    (?:
        \s+
        (?P<pinpoint_type>""" + _PINPOINT_TYPE_PATTERN + r""")
        \s*
        (?P<pinpoint>[\d\w()–\-,.\s]+?)
    )?
    \s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# No-jurisdiction pattern: Title Year §/s/section pinpoint (missing jurisdiction entirely)
# Handles: "Limitation Act 2005 §14(1)."
LEGISLATION_NO_JURIS_PATTERN = regex.compile(
    r"""
    (?P<title>
        (?:[\w'''-]+\s+)*
        (?:Act|Ordinance|Regulation|Regulations|Rules?|Code|Law|Bill|Charter|Constitution|Statute|By-laws?)
    )
    \s+
    (?P<year>\d{4})
    \s*
    (?P<pinpoint_type>""" + _PINPOINT_TYPE_PATTERN + r""")
    \s*
    (?P<pinpoint>[\d\w()–\-,.\s]+?)
    \s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Simpler fallback: detect "Act YYYY" pattern
ACT_YEAR_PATTERN = regex.compile(
    r"""
    (?:Act|Ordinance|Regulations?|Rules?|Code|Law|Bill|Charter|Constitution|Statute|By-laws?)
    \s+\d{4}
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Detect jurisdiction in parentheses (abbreviated or full)
JURISDICTION_PARENS_PATTERN = regex.compile(
    r"\((" + _ALL_JURIS_PATTERN + r")\)",
    regex.UNICODE,
)


class LegislationParser(BaseCitationParser):
    """Parses legislation citations per AGLC4 Part 3."""

    def can_parse(self, text: str) -> float:
        text = normalize_text(text).rstrip(".")

        if LEGISLATION_PATTERN.search(text):
            return 0.95

        if LEGISLATION_BARE_JURIS_PATTERN.search(text):
            return 0.90

        if LEGISLATION_NO_JURIS_PATTERN.search(text):
            return 0.85

        has_act = bool(ACT_YEAR_PATTERN.search(text))
        has_jurisdiction = bool(JURISDICTION_PARENS_PATTERN.search(text))

        if has_act and has_jurisdiction:
            return 0.7
        if has_act:
            return 0.5

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        text_clean = normalize_text(text)

        # Try primary pattern (with bracketed jurisdiction)
        m = LEGISLATION_PATTERN.search(text_clean)
        if m:
            return self._parse_structured(m, text_clean, runs, jurisdiction_format="bracketed")

        # Try bare jurisdiction (no brackets)
        m = LEGISLATION_BARE_JURIS_PATTERN.search(text_clean)
        if m:
            return self._parse_structured(m, text_clean, runs, jurisdiction_format="bare")

        # Try no-jurisdiction pattern
        m = LEGISLATION_NO_JURIS_PATTERN.search(text_clean)
        if m:
            return self._parse_no_jurisdiction(m, text_clean, runs)

        has_act = bool(ACT_YEAR_PATTERN.search(text_clean))
        if has_act:
            return ParseResult(
                source_type=SourceType.LEGISLATION,
                confidence=0.5,
                fields={
                    "raw_text": text_clean,
                    "has_jurisdiction": bool(JURISDICTION_PARENS_PATTERN.search(text_clean)),
                    "parse_error": "could not fully parse legislation citation",
                },
            )

        return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

    def _parse_structured(
        self,
        m: regex.Match,  # type: ignore[type-arg]
        full_text: str,
        runs: list[FootnoteRun],
        jurisdiction_format: str = "bracketed",
    ) -> ParseResult:
        title = m.group("title").strip()
        year = m.group("year")
        jurisdiction_raw = m.group("jurisdiction")
        pinpoint_type = m.group("pinpoint_type")
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()
        if pinpoint_type:
            pinpoint_type = pinpoint_type.strip()

        # Normalise jurisdiction to abbreviation
        if jurisdiction_raw in FULL_NAME_TO_ABBREVIATION:
            jurisdiction = FULL_NAME_TO_ABBREVIATION[jurisdiction_raw]
            jurisdiction_is_full_name = True
        else:
            jurisdiction = jurisdiction_raw
            jurisdiction_is_full_name = False

        # Detect comma before pinpoint
        has_comma_before_pinpoint = False
        if pinpoint_type and jurisdiction_format == "bracketed":
            juris_marker = f"({jurisdiction_raw})"
            jur_pos = full_text.find(juris_marker)
            if jur_pos >= 0:
                jur_end = jur_pos + len(juris_marker)
                between = full_text[jur_end:m.start("pinpoint_type")]
                has_comma_before_pinpoint = "," in between

        # Detect pinpoint type errors
        pinpoint_type_error: str | None = None
        if pinpoint_type and pinpoint_type not in (
            "s", "ss", "reg", "regs", "r", "rr",
            "cl", "cll", "sch", "pt", "div", "para",
        ):
            pinpoint_type_error = pinpoint_type

        # Detect missing space between § and number (e.g., §14(1))
        has_pinpoint_spacing_error = False
        if pinpoint_type and pinpoint:
            pin_start = m.start("pinpoint")
            type_end = m.end("pinpoint_type")
            if pin_start == type_end:  # No space at all
                has_pinpoint_spacing_error = True

        title_year = f"{title} {year}"
        title_is_italic = any(
            r.italic and (title_year in r.text or title in r.text)
            for r in runs
        )

        juris_display = f"({jurisdiction_raw})" if jurisdiction_format == "bracketed" else jurisdiction_raw
        juris_is_italic = any(
            r.italic and juris_display in r.text
            for r in runs
        )

        return ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.95 if jurisdiction_format == "bracketed" else 0.90,
            fields={
                "title": title,
                "year": year,
                "jurisdiction": jurisdiction,
                "jurisdiction_raw": jurisdiction_raw,
                "jurisdiction_format": jurisdiction_format,
                "jurisdiction_is_full_name": jurisdiction_is_full_name,
                "pinpoint_type": pinpoint_type,
                "pinpoint": pinpoint,
                "has_comma_before_pinpoint": has_comma_before_pinpoint,
                "pinpoint_type_error": pinpoint_type_error,
                "has_pinpoint_spacing_error": has_pinpoint_spacing_error,
                "title_is_italic": title_is_italic,
                "jurisdiction_is_italic": juris_is_italic,
            },
        )

    def _parse_no_jurisdiction(
        self,
        m: regex.Match,  # type: ignore[type-arg]
        full_text: str,
        runs: list[FootnoteRun],
    ) -> ParseResult:
        """Parse legislation with missing jurisdiction."""
        title = m.group("title").strip()
        year = m.group("year")
        pinpoint_type = m.group("pinpoint_type")
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()
        if pinpoint_type:
            pinpoint_type = pinpoint_type.strip()

        pinpoint_type_error: str | None = None
        if pinpoint_type and pinpoint_type not in (
            "s", "ss", "reg", "regs", "r", "rr",
            "cl", "cll", "sch", "pt", "div", "para",
        ):
            pinpoint_type_error = pinpoint_type

        has_pinpoint_spacing_error = False
        if pinpoint_type and pinpoint:
            pin_start = m.start("pinpoint")
            type_end = m.end("pinpoint_type")
            if pin_start == type_end:
                has_pinpoint_spacing_error = True

        title_year = f"{title} {year}"
        title_is_italic = any(
            r.italic and (title_year in r.text or title in r.text)
            for r in runs
        )

        return ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.85,
            fields={
                "title": title,
                "year": year,
                "jurisdiction": None,
                "jurisdiction_raw": None,
                "jurisdiction_format": "missing",
                "jurisdiction_is_full_name": False,
                "pinpoint_type": pinpoint_type,
                "pinpoint": pinpoint,
                "has_comma_before_pinpoint": False,
                "pinpoint_type_error": pinpoint_type_error,
                "has_pinpoint_spacing_error": has_pinpoint_spacing_error,
                "title_is_italic": title_is_italic,
                "jurisdiction_is_italic": False,
            },
        )
