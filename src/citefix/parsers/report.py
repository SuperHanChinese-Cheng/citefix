"""Report / government document citation parser (AGLC4 Rule 6.7)."""

from __future__ import annotations

import regex

from citefix.models import FootnoteRun, ParseResult, SourceType
from citefix.parsers.base import BaseCitationParser

# Report-type keywords that appear in the parenthetical descriptor
_REPORT_TYPES = (
    "Report",
    "Final Report",
    "Interim Report",
    "Discussion Paper",
    "Issues Paper",
    "Inquiry Report",
    "Information Paper",
    "White Paper",
    "Green Paper",
    "Research Paper",
)

_REPORT_TYPE_PATTERN = "|".join(
    regex.escape(rt) for rt in sorted(_REPORT_TYPES, key=len, reverse=True)
)

# Common report-producing bodies
_BODY_KEYWORDS = (
    "Commission",
    "Committee",
    "Council",
    "Department",
    "Productivity",
    "Law Reform",
    "Royal Commission",
    "Ombudsman",
    "Auditor",
    "Inspector",
    "Bureau",
    "Treasury",
    "Agency",
    "Authority",
    "Office",
    "Tribunal",
    "Senate",
    "House of Representatives",
    "Parliament",
)

# Pattern WITH body: Body, Title (Report Type [No X], Year) [pinpoint].
# Body must not contain commas (organisation names like "Australian Law Reform Commission").
REPORT_WITH_BODY_PATTERN = regex.compile(
    r"""
    ^
    (?P<body>[^,]+)                         # Authoring body (no commas in body name)
    ,\s+
    (?P<title>[^(]+?)                       # Report title (no open parens — stops before descriptor)
    \s*
    \(
        (?P<report_descriptor>
            (?:""" + _REPORT_TYPE_PATTERN + r""")  # Report type keyword
            (?:\s+No\s+(?P<report_number>[\d]+))?  # Optional "No 129"
        )
        ,\s*
        (?P<year>\d{4})                     # Year
    \)
    (?:
        \s+
        (?P<pinpoint>[\d\-–,\s\[\]]+?)     # Optional pinpoint
    )?
    \s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Pattern WITHOUT body: Title (Report Type [No X], Year) [pinpoint].
# For citations where title alone is used (e.g., Royal Commission reports).
REPORT_TITLE_ONLY_PATTERN = regex.compile(
    r"""
    ^
    (?P<title>.+?)                          # Report title (may contain commas)
    \s*
    \(
        (?P<report_descriptor>
            (?:""" + _REPORT_TYPE_PATTERN + r""")  # Report type keyword
            (?:\s+No\s+(?P<report_number>[\d]+))?  # Optional "No 129"
        )
        ,\s*
        (?P<year>\d{4})                     # Year
    \)
    (?:
        \s+
        (?P<pinpoint>[\d\-–,\s\[\]]+?)     # Optional pinpoint
    )?
    \s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Simpler fallback: detect "(Report" or "(Final Report" etc. with a year in parens
REPORT_DESCRIPTOR_PATTERN = regex.compile(
    r"\(\s*(?:" + _REPORT_TYPE_PATTERN + r")[\s\w]*,\s*\d{4}\s*\)",
    regex.UNICODE,
)

# Body-keyword heuristic for can_parse
_BODY_KEYWORD_PATTERN = regex.compile(
    r"\b(?:" + "|".join(regex.escape(kw) for kw in _BODY_KEYWORDS) + r")\b",
    regex.UNICODE,
)


class ReportParser(BaseCitationParser):
    """Parses report and government document citations per AGLC4 Rule 6.7."""

    def can_parse(self, text: str) -> float:
        text = text.strip().rstrip(".")

        if REPORT_WITH_BODY_PATTERN.search(text):
            return 0.90

        if REPORT_TITLE_ONLY_PATTERN.search(text):
            return 0.90

        if REPORT_DESCRIPTOR_PATTERN.search(text):
            has_body = bool(_BODY_KEYWORD_PATTERN.search(text))
            return 0.75 if has_body else 0.65

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        text_clean = text.strip()

        # Try body + title pattern first, but only accept if the body
        # looks like an actual organisation name (contains a body keyword
        # and ends cleanly — not mid-phrase like "...in the Banking")
        m = REPORT_WITH_BODY_PATTERN.search(text_clean)
        if m and self._is_valid_body(m.group("body")):
            return self._parse_structured(m, runs, has_body=True)

        # Try title-only pattern (title may contain commas)
        m = REPORT_TITLE_ONLY_PATTERN.search(text_clean)
        if m:
            return self._parse_structured(m, runs, has_body=False)

        if REPORT_DESCRIPTOR_PATTERN.search(text_clean):
            return ParseResult(
                source_type=SourceType.REPORT,
                confidence=0.5,
                fields={
                    "raw_text": text_clean,
                    "parse_error": "could not fully parse report citation",
                },
            )

        return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

    @staticmethod
    def _is_valid_body(body_candidate: str) -> bool:
        """Check whether a body candidate looks like an actual organisation name.

        Returns False if it looks like a fragment of a longer title that was
        split at an internal comma (e.g., "Royal Commission into Misconduct in the Banking").
        A valid body ends with the organisation keyword itself, not with
        trailing descriptive words.
        """
        body = body_candidate.strip()
        if not _BODY_KEYWORD_PATTERN.search(body):
            return False
        # A valid body should end with an organisation keyword (possibly followed by
        # a short qualifier like "of Australia"). If the body has many words after
        # the last body keyword, it's likely a split title fragment.
        last_keyword_pos = -1
        for kw in _BODY_KEYWORDS:
            pos = body.rfind(kw)
            if pos >= 0:
                end = pos + len(kw)
                if end > last_keyword_pos:
                    last_keyword_pos = end
        if last_keyword_pos < 0:
            return False
        # Allow a short suffix after the keyword (e.g., " of Australia", " (Cth)")
        suffix = body[last_keyword_pos:].strip()
        # If more than ~30 chars remain after the last keyword, it's likely a title fragment
        if len(suffix) > 20:
            return False
        return True

    def _parse_structured(
        self,
        m: regex.Match,  # type: ignore[type-arg]
        runs: list[FootnoteRun],
        *,
        has_body: bool,
    ) -> ParseResult:
        body = m.group("body").strip() if has_body else None
        title = m.group("title").strip()
        report_descriptor = m.group("report_descriptor").strip()
        report_number = m.group("report_number")
        year = m.group("year")
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()

        # Check if the title is italicised in the runs
        title_is_italic = any(r.italic and title in r.text for r in runs)

        return ParseResult(
            source_type=SourceType.REPORT,
            confidence=0.90,
            fields={
                "body": body,
                "title": title,
                "report_descriptor": report_descriptor,
                "report_number": report_number,
                "year": year,
                "pinpoint": pinpoint,
                "title_is_italic": title_is_italic,
            },
        )
