"""Treaty / international material citation parser (AGLC4 Rule 9.1)."""

from __future__ import annotations

import regex

from citefix.models import FootnoteRun, ParseResult, SourceType
from citefix.parsers.base import BaseCitationParser

# Months for date parsing
_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTH_PATTERN = "|".join(_MONTHS)

# Date pattern: day month year  (e.g., "16 December 1966")
_DATE_PATTERN = r"\d{1,2}\s+(?:" + _MONTH_PATTERN + r")\s+\d{4}"

# Treaty series abbreviations
_TREATY_SERIES = (
    "UNTS",      # United Nations Treaty Series
    "LNTS",      # League of Nations Treaty Series
    "ATS",       # Australian Treaty Series
    "UKTS",      # United Kingdom Treaty Series
    "TIAS",      # Treaties and Other International Acts Series
    "ILM",       # International Legal Materials
    "CTS",       # Consolidated Treaty Series
    "NZTS",      # New Zealand Treaty Series
)

_TREATY_SERIES_PATTERN = "|".join(
    regex.escape(s) for s in sorted(_TREATY_SERIES, key=len, reverse=True)
)

# Full treaty pattern:
# Title, opened for signature Date, Volume Series Page (entered into force Date).
TREATY_PATTERN = regex.compile(
    r"""
    ^
    (?P<title>.+?)                              # Treaty title (italicised)
    ,\s+
    opened\s+for\s+signature\s+
    (?P<opened_date>""" + _DATE_PATTERN + r""") # Date opened for signature
    ,\s+
    (?P<volume>\d+)                             # Volume number
    \s+
    (?P<treaty_series>""" + _TREATY_SERIES_PATTERN + r""")  # Treaty series
    \s+
    (?P<start_page>\d+)                         # Starting page
    \s+
    \(
        entered\s+into\s+force\s+
        (?P<force_date>""" + _DATE_PATTERN + r""")  # Date entered into force
    \)
    (?:
        \s+
        (?P<pinpoint>[\d\-–,\s\[\]]+?)         # Optional pinpoint
    )?
    \s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Simpler pattern: detect "opened for signature" phrase
OPENED_SIGNATURE_PATTERN = regex.compile(
    r"opened\s+for\s+signature",
    regex.UNICODE | regex.IGNORECASE,
)

# Detect "entered into force" phrase
ENTERED_FORCE_PATTERN = regex.compile(
    r"entered\s+into\s+force",
    regex.UNICODE | regex.IGNORECASE,
)

# Detect treaty series reference (volume + series abbreviation)
TREATY_SERIES_REF_PATTERN = regex.compile(
    r"\d+\s+(?:" + _TREATY_SERIES_PATTERN + r")\s+\d+",
    regex.UNICODE,
)

# Common treaty title keywords for heuristic matching
_TREATY_KEYWORDS = (
    "Convention",
    "Covenant",
    "Protocol",
    "Treaty",
    "Agreement",
    "Charter",
    "Statute",
    "Declaration",
)

_TREATY_KEYWORD_PATTERN = regex.compile(
    r"\b(?:" + "|".join(regex.escape(kw) for kw in _TREATY_KEYWORDS) + r")\b",
    regex.UNICODE,
)


class TreatyParser(BaseCitationParser):
    """Parses treaty / international material citations per AGLC4 Rule 9.1."""

    def can_parse(self, text: str) -> float:
        text = text.strip().rstrip(".")

        if TREATY_PATTERN.search(text):
            return 0.90

        has_opened = bool(OPENED_SIGNATURE_PATTERN.search(text))
        has_force = bool(ENTERED_FORCE_PATTERN.search(text))
        has_series = bool(TREATY_SERIES_REF_PATTERN.search(text))
        has_keyword = bool(_TREATY_KEYWORD_PATTERN.search(text))

        if has_opened and has_force and has_series:
            return 0.80

        if has_opened and has_series:
            return 0.70

        if has_keyword and has_series:
            return 0.60

        if has_opened or (has_keyword and has_force):
            return 0.45

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        text_clean = text.strip()

        m = TREATY_PATTERN.search(text_clean)
        if m:
            return self._parse_structured(m, runs)

        has_opened = bool(OPENED_SIGNATURE_PATTERN.search(text_clean))
        has_series = bool(TREATY_SERIES_REF_PATTERN.search(text_clean))
        if has_opened or has_series:
            return ParseResult(
                source_type=SourceType.TREATY,
                confidence=0.5,
                fields={
                    "raw_text": text_clean,
                    "parse_error": "could not fully parse treaty citation",
                },
            )

        return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

    def _parse_structured(
        self,
        m: regex.Match,  # type: ignore[type-arg]
        runs: list[FootnoteRun],
    ) -> ParseResult:
        title = m.group("title").strip()
        opened_date = m.group("opened_date").strip()
        volume = m.group("volume")
        treaty_series = m.group("treaty_series")
        start_page = m.group("start_page")
        force_date = m.group("force_date").strip()
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()

        # Check if the title is italicised in the runs
        title_is_italic = any(r.italic and title in r.text for r in runs)

        return ParseResult(
            source_type=SourceType.TREATY,
            confidence=0.90,
            fields={
                "title": title,
                "opened_date": opened_date,
                "volume": volume,
                "treaty_series": treaty_series,
                "start_page": start_page,
                "force_date": force_date,
                "pinpoint": pinpoint,
                "title_is_italic": title_is_italic,
            },
        )
