"""Website / online source citation parser (AGLC4 Rule 6.9)."""

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

# URL in angle brackets: <https://...>
URL_ANGLE_BRACKET_PATTERN = regex.compile(
    r"<(?P<url>https?://[^\s>]+)>",
    regex.UNICODE,
)

# Full website pattern:
# Author, 'Title' [, Website Name] (Descriptor, Date) <URL>.
# OR: Author, 'Title' [, Website Name] (Date) <URL>.
WEBSITE_PATTERN = regex.compile(
    r"""
    ^
    (?P<author>.+?)                         # Author / organisation
    ,\s+
    '(?P<title>[^']+)'                      # Title in single quotes
    (?:
        ,\s+
        (?P<website_name>[^(]+?)            # Optional website name
    )?
    \s*
    \(
        (?:
            (?P<descriptor>[^,)]+?)         # Optional descriptor (e.g., "Web Page", "Report")
            ,\s*
        )?
        (?P<date>
            (?:
                (?:\d{1,2}\s+)?             # Optional day
                (?:""" + _MONTH_PATTERN + r""")  # Month
                \s+
            )?                              # Month (with optional day) is optional
            \d{4}                           # Year
        )
    \)
    \s*
    <(?P<url>https?://[^\s>]+)>             # URL in angle brackets
    \s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# Simpler fallback: any text with a URL in angle brackets
URL_IN_BRACKETS_PATTERN = regex.compile(
    r"<https?://[^\s>]+>",
    regex.UNICODE,
)

# Detect single-quoted title
SINGLE_QUOTED_TITLE_PATTERN = regex.compile(
    r"'[^']+'",
    regex.UNICODE,
)

# Detect double-quoted title (common error)
DOUBLE_QUOTED_TITLE_PATTERN = regex.compile(
    r'"[^"]+"',
    regex.UNICODE,
)

# Bare URL without angle brackets
BARE_URL_PATTERN = regex.compile(
    r"(?<![<])https?://\S+(?![>])",
    regex.UNICODE,
)


class WebsiteParser(BaseCitationParser):
    """Parses website / online source citations per AGLC4 Rule 6.9."""

    def can_parse(self, text: str) -> float:
        text = text.strip().rstrip(".")

        if WEBSITE_PATTERN.search(text):
            return 0.90

        has_url_brackets = bool(URL_IN_BRACKETS_PATTERN.search(text))
        has_bare_url = bool(BARE_URL_PATTERN.search(text))
        has_quoted_title = bool(SINGLE_QUOTED_TITLE_PATTERN.search(text))

        if has_url_brackets and has_quoted_title:
            return 0.75

        if has_url_brackets:
            return 0.65

        if has_bare_url:
            return 0.50

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        text_clean = text.strip()

        m = WEBSITE_PATTERN.search(text_clean)
        if m:
            return self._parse_structured(m, text_clean, runs)

        has_url = bool(URL_IN_BRACKETS_PATTERN.search(text_clean)) or bool(
            BARE_URL_PATTERN.search(text_clean)
        )
        if has_url:
            return self._parse_partial(text_clean, runs)

        return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

    def _parse_structured(
        self,
        m: regex.Match,  # type: ignore[type-arg]
        full_text: str,
        runs: list[FootnoteRun],
    ) -> ParseResult:
        author = m.group("author").strip()
        title = m.group("title").strip()
        website_name = m.group("website_name")
        descriptor = m.group("descriptor")
        date = m.group("date").strip()
        url = m.group("url").strip()

        if website_name:
            website_name = website_name.strip()
        if descriptor:
            descriptor = descriptor.strip()

        # Check for double-quoted title (common error)
        has_double_quote_error = bool(DOUBLE_QUOTED_TITLE_PATTERN.search(full_text))

        # Check if URL is in angle brackets (should be)
        url_in_angle_brackets = bool(URL_ANGLE_BRACKET_PATTERN.search(full_text))

        return ParseResult(
            source_type=SourceType.WEBSITE,
            confidence=0.90,
            fields={
                "author": author,
                "title": title,
                "website_name": website_name,
                "descriptor": descriptor,
                "date": date,
                "url": url,
                "has_double_quote_error": has_double_quote_error,
                "url_in_angle_brackets": url_in_angle_brackets,
            },
        )

    def _parse_partial(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        """Fallback parse when the full pattern doesn't match but a URL is present."""
        url: str | None = None
        url_in_angle_brackets = False

        m_url = URL_ANGLE_BRACKET_PATTERN.search(text)
        if m_url:
            url = m_url.group("url")
            url_in_angle_brackets = True
        else:
            m_bare = BARE_URL_PATTERN.search(text)
            if m_bare:
                url = m_bare.group(0)

        has_double_quote_error = bool(DOUBLE_QUOTED_TITLE_PATTERN.search(text))

        return ParseResult(
            source_type=SourceType.WEBSITE,
            confidence=0.5,
            fields={
                "raw_text": text,
                "url": url,
                "url_in_angle_brackets": url_in_angle_brackets,
                "has_double_quote_error": has_double_quote_error,
                "parse_error": "could not fully parse website citation",
            },
        )
