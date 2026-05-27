"""Case citation parser (AGLC4 Part 2)."""

from __future__ import annotations

import regex

from citefix.text_utils import normalize_text
from citefix.models import FootnoteRun, ParseResult, SourceType
from citefix.parsers.base import BaseCitationParser
from citefix.rules.abbreviations import ALL_REPORT_SERIES, is_medium_neutral

_REPORT_SERIES_PATTERN = "|".join(
    regex.escape(s) for s in sorted(ALL_REPORT_SERIES, key=len, reverse=True)
)

# "v", "V", "vs", "vs.", "versus" — captures the separator for error detection
_V_SEPARATOR = r"(?:vs\.?|versus|[vV])"

# Matches: Party v Party (Year) Vol Report Page OR Party v Party [Year] Court Number
CASE_PATTERN = regex.compile(
    r"""
    (?P<parties>
        .+?                         # Party names (lazy — stops at year bracket)
        \s+""" + _V_SEPARATOR + r"""\s+  # "v"/"vs"/"versus" separator
        .+?                         # Second party
    )
    \s*,?\s*                        # Allow optional comma before year bracket
    (?P<year_bracket>[(\[])         # Opening bracket for year
    (?P<year>\d{4})                 # Four-digit year
    (?P<year_close>[)\]])           # Closing bracket
    \s*,?\s*                        # Allow optional comma after year bracket
    (?:(?P<volume>\d+)\s+)?         # Optional volume number
    (?P<report_series>""" + _REPORT_SERIES_PATTERN + r""")
    \s+
    (?P<start_page>\d+)             # Starting page/paragraph number
    (?:
        \s*,?\s*                    # Optional comma
        (?:at\s+)?                  # Optional "at"
        (?:p\.?\s*|pp\.?\s*|pages?\s+|para(?:graph)?\.?\s+)?  # Optional prefix
        (?P<pinpoint>
            \[?\d+\]?               # Pinpoint (possibly in square brackets)
            (?:\s*[-–]\s*\[?\d+\]?)? # Optional range
        )
    )?
    \s*\.?\s*(?:$|(?=\s*;))
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Simpler pattern for "v" detection when the full pattern doesn't match
V_PATTERN = regex.compile(
    r"""
    .+                              # At least some text before
    \s+""" + _V_SEPARATOR + r"""\s+ # "v", "vs", "vs.", "versus"
    .+                              # At least some text after
    [\(\[]\d{4}[\)\]]               # Year in brackets
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Medium-neutral pattern: Party v Party [Year] Court Number
# Also accepts (Year) with round brackets (which will be flagged as wrong)
MEDIUM_NEUTRAL_PATTERN = regex.compile(
    r"""
    (?P<parties>.+?\s+""" + _V_SEPARATOR + r"""\s+.+?)
    \s*,?\s*
    (?P<year_bracket>[(\[])(?P<year>\d{4})(?P<year_close>[)\]])
    \s*,?\s*
    (?P<court>[A-Z]{2,8})
    \s+
    (?P<number>\d+)
    (?:
        \s*,?\s*
        (?:at\s+)?
        (?:pp?\.?\s*|pages?\s+|para(?:graph)?\.?\s+)?
        (?P<pinpoint>\[?\d+\]?(?:\s*[-–]\s*\[?\d+\]?)?)
    )?
    \s*\.?\s*(?:$|(?=\s*;))
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Non-adversarial case name prefix — "Re", "Ex parte", "In re", "In the matter of"
_RE_PREFIX = r"(?:Re|Ex\s+[Pp]arte|In\s+re|In\s+the\s+[Mm]atter\s+of)"

# Non-adversarial reported pattern: Re X (Year) Vol Report Page
RE_CASE_PATTERN = regex.compile(
    r"""
    (?P<parties>""" + _RE_PREFIX + r"""\s+.+?)
    \s+
    (?P<year_bracket>[(\[])
    (?P<year>\d{4})
    (?P<year_close>[)\]])
    \s+
    (?:(?P<volume>\d+)\s+)?
    (?P<report_series>""" + _REPORT_SERIES_PATTERN + r""")
    \s+
    (?P<start_page>\d+)
    (?:
        \s*,?\s*
        (?:at\s+)?
        (?:p\.?\s*|pp\.?\s*|pages?\s+|para(?:graph)?\.?\s+)?
        (?P<pinpoint>
            \[?\d+\]?
            (?:\s*[-–]\s*\[?\d+\]?)?
        )
    )?
    \s*\.?\s*(?:$|(?=\s*;))
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Non-adversarial medium-neutral pattern: Re X [Year] Court Number
RE_MEDIUM_NEUTRAL_PATTERN = regex.compile(
    r"""
    (?P<parties>""" + _RE_PREFIX + r"""\s+.+?)
    \s+
    (?P<year_bracket>[(\[])
    (?P<year>\d{4})
    (?P<year_close>[)\]])
    \s+
    (?P<court>[A-Z]{2,8})
    \s+
    (?P<number>\d+)
    (?:
        \s*,?\s*
        (?:at\s+)?
        (?:pp?\.?\s*|pages?\s+|para(?:graph)?\.?\s+)?
        (?P<pinpoint>\[?\d+\]?(?:\s*[-–]\s*\[?\d+\]?)?)
    )?
    \s*\.?\s*(?:$|(?=\s*;))
    """,
    regex.VERBOSE | regex.UNICODE,
)


class CaseCitationParser(BaseCitationParser):
    """Parses case citations per AGLC4 Part 2."""

    def can_parse(self, text: str) -> float:
        text = normalize_text(text).rstrip(".")

        if CASE_PATTERN.search(text):
            return 0.95

        if MEDIUM_NEUTRAL_PATTERN.search(text):
            return 0.90

        if RE_CASE_PATTERN.search(text):
            return 0.90

        if RE_MEDIUM_NEUTRAL_PATTERN.search(text):
            return 0.90

        if V_PATTERN.search(text):
            return 0.6

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        text_clean = normalize_text(text)

        m = CASE_PATTERN.search(text_clean)
        if m:
            return self._parse_reported(m, runs)

        m = MEDIUM_NEUTRAL_PATTERN.search(text_clean)
        if m:
            return self._parse_medium_neutral(m, runs)

        m = RE_CASE_PATTERN.search(text_clean)
        if m:
            return self._parse_re_case(m, runs)

        m = RE_MEDIUM_NEUTRAL_PATTERN.search(text_clean)
        if m:
            return self._parse_re_medium_neutral(m, runs)

        if V_PATTERN.search(text_clean):
            return ParseResult(
                source_type=SourceType.CASE,
                confidence=0.4,
                fields={"raw_text": text_clean, "parse_error": "could not extract structured fields"},
            )

        return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

    def _parse_reported(self, m: regex.Match, runs: list[FootnoteRun]) -> ParseResult:  # type: ignore[type-arg]
        parties = m.group("parties").strip().rstrip(",")
        year = m.group("year")
        year_bracket_open = m.group("year_bracket")
        year_bracket_close = m.group("year_close")
        volume = m.group("volume")
        report_series = m.group("report_series")
        start_page = m.group("start_page")
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()

        has_v_error = False
        parties_lower = parties.lower()
        for bad in (" vs ", " vs. ", " versus "):
            if bad in parties_lower:
                has_v_error = True
                break
        # Also check for uppercase "V" (should be lowercase "v")
        if not has_v_error and regex.search(r"\s+V\s+", parties):
            has_v_error = True

        # Detect "v." (v with period) in parties text — AGLC4 requires plain "v"
        has_v_period = bool(regex.search(r"\bv\.\s", parties))

        # Detect "(No.)" with period — AGLC4 requires "(No X)" without period
        has_no_period = "(No." in parties

        return ParseResult(
            source_type=SourceType.CASE,
            confidence=0.95,
            fields={
                "parties": parties,
                "year": year,
                "year_bracket_open": year_bracket_open,
                "year_bracket_close": year_bracket_close,
                "volume": volume,
                "report_series": report_series,
                "start_page": start_page,
                "pinpoint": pinpoint,
                "is_medium_neutral": is_medium_neutral(report_series),
                "has_v_error": has_v_error,
                "has_v_period": has_v_period,
                "has_no_period": has_no_period,
                "italic_runs": [r for r in runs if r.italic],
            },
        )

    def _parse_medium_neutral(self, m: regex.Match, runs: list[FootnoteRun]) -> ParseResult:  # type: ignore[type-arg]
        parties = m.group("parties").strip().rstrip(",")
        year = m.group("year")
        year_bracket_open = m.group("year_bracket")
        court = m.group("court")
        number = m.group("number")
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()

        has_v_error = False
        parties_lower = parties.lower()
        for bad in (" vs ", " vs. ", " versus "):
            if bad in parties_lower:
                has_v_error = True
                break
        # Also check for uppercase "V" (should be lowercase "v")
        if not has_v_error and regex.search(r"\s+V\s+", parties):
            has_v_error = True

        # Detect "v." (v with period) in parties text — AGLC4 requires plain "v"
        has_v_period = bool(regex.search(r"\bv\.\s", parties))

        # Detect "(No.)" with period — AGLC4 requires "(No X)" without period
        has_no_period = "(No." in parties

        return ParseResult(
            source_type=SourceType.CASE,
            confidence=0.90,
            fields={
                "parties": parties,
                "year": year,
                "year_bracket_open": year_bracket_open,
                "year_bracket_close": m.group("year_close"),
                "volume": None,
                "report_series": court,
                "start_page": number,
                "pinpoint": pinpoint,
                "is_medium_neutral": True,
                "has_v_error": has_v_error,
                "has_v_period": has_v_period,
                "has_no_period": has_no_period,
                "italic_runs": [r for r in runs if r.italic],
            },
        )

    def _parse_re_case(self, m: regex.Match, runs: list[FootnoteRun]) -> ParseResult:  # type: ignore[type-arg]
        """Parse a non-adversarial reported case (Re/Ex parte/In re/In the matter of)."""
        parties = m.group("parties").strip()
        year = m.group("year")
        year_bracket_open = m.group("year_bracket")
        year_bracket_close = m.group("year_close")
        volume = m.group("volume")
        report_series = m.group("report_series")
        start_page = m.group("start_page")
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()

        # Detect "(No.)" with period — AGLC4 requires "(No X)" without period
        has_no_period = "(No." in parties

        return ParseResult(
            source_type=SourceType.CASE,
            confidence=0.90,
            fields={
                "parties": parties,
                "year": year,
                "year_bracket_open": year_bracket_open,
                "year_bracket_close": year_bracket_close,
                "volume": volume,
                "report_series": report_series,
                "start_page": start_page,
                "pinpoint": pinpoint,
                "is_medium_neutral": is_medium_neutral(report_series),
                "has_v_error": False,
                "has_v_period": False,
                "has_no_period": has_no_period,
                "italic_runs": [r for r in runs if r.italic],
            },
        )

    def _parse_re_medium_neutral(self, m: regex.Match, runs: list[FootnoteRun]) -> ParseResult:  # type: ignore[type-arg]
        """Parse a non-adversarial medium-neutral case (Re/Ex parte with court identifier)."""
        parties = m.group("parties").strip()
        year = m.group("year")
        year_bracket_open = m.group("year_bracket")
        court = m.group("court")
        number = m.group("number")
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()

        # Detect "(No.)" with period — AGLC4 requires "(No X)" without period
        has_no_period = "(No." in parties

        return ParseResult(
            source_type=SourceType.CASE,
            confidence=0.90,
            fields={
                "parties": parties,
                "year": year,
                "year_bracket_open": year_bracket_open,
                "year_bracket_close": m.group("year_close"),
                "volume": None,
                "report_series": court,
                "start_page": number,
                "pinpoint": pinpoint,
                "is_medium_neutral": True,
                "has_v_error": False,
                "has_v_period": False,
                "has_no_period": has_no_period,
                "italic_runs": [r for r in runs if r.italic],
            },
        )
