"""Ibid and subsequent reference parsers (AGLC4 Rules 1.4.1 and 1.4.2)."""

from __future__ import annotations

import regex

from citefix.text_utils import normalize_text
from citefix.models import FootnoteRun, ParseResult, SourceType
from citefix.parsers.base import BaseCitationParser

# ---------------------------------------------------------------------------
# Ibid patterns
# ---------------------------------------------------------------------------

# Matches "Ibid", "ibid", "Id", "id" with optional pinpoint and trailing full stop.
# Named groups:
#   keyword  — the ibid/id keyword itself
#   pinpoint — optional page/paragraph number after the keyword
#   fullstop — trailing full stop (if present)
IBID_PATTERN = regex.compile(
    r"""
    ^\s*
    (?P<signal>(?:See\s+(?:also|eg,?\s*|especially|generally)\s*|But\s+see\s+|Cf\s+)?)  # Optional introductory signal
    (?P<keyword>[Ii]bid|[Ii]d)  # "Ibid", "ibid", "Id", "id"
    (?:
        \.?                     # Optional period after keyword (e.g., "Id.")
        (?P<comma>,)?           # Detect comma (error per AGLC4 1.4.3)
        \s+(?:at\s+)?           # Optional "at" (non-AGLC4 style: "Id. at 55")
        (?:(?:p|pp)\.?\s+)?     # Optional "p." or "pp." prefix
        (?P<pinpoint>
            \[?\d+\]?               # Page or paragraph number, optionally in brackets
            (?:\s*[–\-]\s*\[?\d+\]?)?  # Optional range (en-dash or hyphen)
        )
    )?
    \s*
    (?P<fullstop>\.)?           # Trailing full stop
    \s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# ---------------------------------------------------------------------------
# Subsequent reference patterns
# ---------------------------------------------------------------------------

# Matches: Short title (n X) [pinpoint].
# Named groups:
#   short_title  — the short title before the parenthetical
#   footnote_ref — the footnote number inside (n X)
#   pinpoint     — optional pinpoint after the parenthetical
#   fullstop     — trailing full stop (if present)
SUBSEQUENT_REF_PATTERN = regex.compile(
    r"""
    ^\s*
    (?P<short_title>.+?)        # Short title (lazy — stops at "(n")
    \s+
    \(n\s*(?P<footnote_ref>\d+)\)  # (n X) — footnote cross-reference
    (?:\s+(?P<pinpoint>
        (?:s\s+)?               # Optional section prefix "s 180"
        \[?\d+\]?               # Page/paragraph number
        (?:\s*[–\-]\s*\[?\d+\]?)?  # Optional range
        (?:\([a-zA-Z0-9]+\))?   # Optional subsection e.g. (1)
    ))?
    \s*
    (?P<fullstop>\.)?           # Trailing full stop
    \s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)


# ---------------------------------------------------------------------------
# Non-AGLC4 subsequent reference patterns
# ---------------------------------------------------------------------------

# "above n X" pattern: e.g. "McCutcheon, above n 13, 920."
ABOVE_N_PATTERN = regex.compile(
    r"""
    ^\s*
    (?P<short_title>.+?),?\s+
    above\s+n(?:ote)?\s+
    (?P<footnote_ref>\d+)
    (?:,?\s*(?P<pinpoint>.+?))?\s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)

# "(note X)" pattern: e.g. "Palmer v Ayres (note 4) [31]."
NOTE_X_PATTERN = regex.compile(
    r"""
    ^\s*
    (?P<short_title>.+?)\s+
    \(note\s+(?P<footnote_ref>\d+)\)
    \s*,?\s*
    (?P<pinpoint>.+?)?\s*\.?\s*$
    """,
    regex.VERBOSE | regex.UNICODE,
)


class IbidParser(BaseCitationParser):
    """Parses 'Ibid' citations per AGLC4 Rule 1.4.1.

    Detects:
    - "Ibid." — same source, same pinpoint as preceding footnote
    - "Ibid 55." — same source, different pinpoint
    - Common errors: lowercase "ibid", "Id."/"id.", missing full stop
    """

    def can_parse(self, text: str) -> float:
        """Return confidence that this text is an Ibid reference.

        Args:
            text: Plain text of the footnote.

        Returns:
            Confidence score. High (0.95) for clear Ibid patterns.
        """
        text_stripped = text.strip()

        if IBID_PATTERN.match(text_stripped):
            return 0.95

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        """Parse an Ibid footnote into structured fields.

        Args:
            text: Plain text of the footnote.
            runs: Formatted runs (preserves italic/bold info for validation).

        Returns:
            ParseResult with source_type=IBID and extracted fields.
        """
        text_stripped = text.strip()
        m = IBID_PATTERN.match(text_stripped)

        if not m:
            return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

        signal = m.group("signal")
        keyword = m.group("keyword")
        comma = m.group("comma")
        pinpoint = m.group("pinpoint")
        fullstop = m.group("fullstop")

        if pinpoint:
            pinpoint = pinpoint.strip()
        if signal:
            signal = signal.strip()

        has_signal = bool(signal)
        has_comma_before_pinpoint = comma == ","
        is_capitalised = keyword[0] == "I"
        is_id_variant = keyword.lower() == "id"
        has_full_stop = fullstop == "."

        # Check if "Ibid" is italicised in the runs
        is_italic = any(
            r.italic and keyword in r.text
            for r in runs
        )

        return ParseResult(
            source_type=SourceType.IBID,
            confidence=0.95,
            fields={
                "is_ibid": True,
                "keyword": keyword,
                "pinpoint": pinpoint,
                "is_capitalised": is_capitalised,
                "is_id_variant": is_id_variant,
                "has_full_stop": has_full_stop,
                "is_italic": is_italic,
                "has_signal": has_signal,
                "signal": signal or "",
                "has_comma_before_pinpoint": has_comma_before_pinpoint,
                "raw_text": text_stripped,
            },
        )


class SubsequentRefParser(BaseCitationParser):
    """Parses subsequent references per AGLC4 Rule 1.4.2.

    Format: Short title (n X) pinpoint.

    Examples:
    - Mabo (n 3) 55.
    - Palmer (n 1).
    - Corporations Act (n 5) s 180.
    """

    def can_parse(self, text: str) -> float:
        """Return confidence that this text is a subsequent reference.

        Args:
            text: Plain text of the footnote.

        Returns:
            Confidence score. High (0.90) for clear (n X) patterns.
        """
        text_stripped = normalize_text(text)

        if SUBSEQUENT_REF_PATTERN.match(text_stripped):
            return 0.90

        # Non-AGLC4 "above n X" pattern
        if ABOVE_N_PATTERN.match(text_stripped):
            return 0.85

        # Non-AGLC4 "(note X)" pattern
        if NOTE_X_PATTERN.match(text_stripped):
            return 0.85

        # Fallback: look for the (n X) pattern anywhere in the text
        if regex.search(r"\(n\s*\d+\)", text_stripped):
            return 0.75

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        """Parse a subsequent reference into structured fields.

        Args:
            text: Plain text of the footnote.
            runs: Formatted runs (preserves italic/bold info for validation).

        Returns:
            ParseResult with source_type=SUBSEQUENT_REF and extracted fields.
        """
        text_stripped = normalize_text(text)
        m = SUBSEQUENT_REF_PATTERN.match(text_stripped)

        if not m:
            # Try non-AGLC4 "above n X" pattern
            m_above = ABOVE_N_PATTERN.match(text_stripped)
            if m_above:
                return self._parse_above_n(m_above, text_stripped)

            # Try non-AGLC4 "(note X)" pattern
            m_note = NOTE_X_PATTERN.match(text_stripped)
            if m_note:
                return self._parse_note_x(m_note, text_stripped)

            # Fallback: if we detected (n X) but couldn't fully parse
            fn_ref_match = regex.search(r"\(n\s*(\d+)\)", text_stripped)
            if fn_ref_match:
                return ParseResult(
                    source_type=SourceType.SUBSEQUENT_REF,
                    confidence=0.5,
                    fields={
                        "raw_text": text_stripped,
                        "footnote_ref": int(fn_ref_match.group(1)),
                        "parse_error": "could not fully parse subsequent reference",
                    },
                )
            return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

        short_title = m.group("short_title").strip()
        footnote_ref = int(m.group("footnote_ref"))
        pinpoint = m.group("pinpoint")
        fullstop = m.group("fullstop")

        if pinpoint:
            pinpoint = pinpoint.strip()

        has_full_stop = fullstop == "."

        return ParseResult(
            source_type=SourceType.SUBSEQUENT_REF,
            confidence=0.90,
            fields={
                "short_title": short_title,
                "footnote_ref": footnote_ref,
                "pinpoint": pinpoint,
                "has_full_stop": has_full_stop,
                "raw_text": text_stripped,
            },
        )

    def _parse_above_n(self, m: regex.Match, raw_text: str) -> ParseResult:  # type: ignore[type-arg]
        """Parse non-AGLC4 'above n X' subsequent reference."""
        short_title = m.group("short_title").strip()
        footnote_ref = int(m.group("footnote_ref"))
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()
            if not pinpoint:
                pinpoint = None

        return ParseResult(
            source_type=SourceType.SUBSEQUENT_REF,
            confidence=0.85,
            fields={
                "short_title": short_title,
                "footnote_number": footnote_ref,
                "pinpoint": pinpoint,
                "format_error": "above_n",
                "raw_text": raw_text,
            },
        )

    def _parse_note_x(self, m: regex.Match, raw_text: str) -> ParseResult:  # type: ignore[type-arg]
        """Parse non-AGLC4 '(note X)' subsequent reference."""
        short_title = m.group("short_title").strip()
        footnote_ref = int(m.group("footnote_ref"))
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()
            if not pinpoint:
                pinpoint = None

        return ParseResult(
            source_type=SourceType.SUBSEQUENT_REF,
            confidence=0.85,
            fields={
                "short_title": short_title,
                "footnote_number": footnote_ref,
                "pinpoint": pinpoint,
                "format_error": "note_x",
                "raw_text": raw_text,
            },
        )
