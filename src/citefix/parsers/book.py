"""Book and chapter citation parser (AGLC4 Rules 5.2 and 5.3)."""

from __future__ import annotations

import regex

from citefix.models import FootnoteRun, ParseResult, SourceType
from citefix.parsers.base import BaseCitationParser

# ---- Helpers ----------------------------------------------------------------

_AUTHOR_WORD = r"[\p{Lu}][\p{L}'\-]+"
_AUTHOR_NAME = rf"(?:{_AUTHOR_WORD}(?:\s+{_AUTHOR_WORD})*)"
_AUTHOR_LIST = (
    rf"(?:{_AUTHOR_NAME}(?:,\s+{_AUTHOR_NAME})*"
    rf"(?:\s+and\s+{_AUTHOR_NAME})?(?:\s+et\s+al)?)"
)

_EDITION = (
    r"(?P<edition_raw>"
    r"(?P<edition_num>\d+(?:st|nd|rd|th))\s+"
    r"(?P<edition_word>ed(?:ition|n)?)"
    r")"
)

_IMPRINT = (
    r"\(\s*"
    r"(?P<publisher>[^,]+?)"
    r",\s*"
    r"(?:" + _EDITION + r",\s*)?"
    r"(?P<year>\d{4})"
    r"\s*\)"
)

_PINPOINT = (
    r"(?:\s+"
    r"(?P<pinpoint_prefix>(?:pp?\.?\s*|pages?\s+))?"
    r"(?P<pinpoint>\d+(?:\s*[-–]\s*\d+)?)"
    r")?"
)

# ---- Quote character classes ------------------------------------------------
_LSINGLE = "‘"
_RSINGLE = "’"
_LDOUBLE = "“"
_RDOUBLE = "”"

_ANY_QUOTE = "['" + _LSINGLE + _RSINGLE + '"' + _LDOUBLE + _RDOUBLE + "]"
_DOUBLE_QUOTE_CHARS = '["' + _LDOUBLE + _RDOUBLE + "]"

_DOUBLE_QUOTES = {'"', _LDOUBLE, _RDOUBLE}


# ---- Full book pattern ------------------------------------------------------
BOOK_PATTERN = regex.compile(
    r"^(?P<author>" + _AUTHOR_LIST + r"),\s+"
    r"(?|"
    r"(?P<title_quote>" + _DOUBLE_QUOTE_CHARS + r")(?P<title>.+?)" + _DOUBLE_QUOTE_CHARS
    + r"|"
    r"(?P<title_quote>)(?P<title>.+?)"
    r")\s+"
    + _IMPRINT
    + _PINPOINT
    + r"\s*\.?\s*$",
    regex.UNICODE,
)

# ---- Chapter-in-edited-book pattern -----------------------------------------
CHAPTER_PATTERN = regex.compile(
    r"^(?P<author>" + _AUTHOR_LIST + r"),\s+"
    r"(?P<chapter_quote>" + _ANY_QUOTE + r")"
    r"(?P<chapter_title>.+?)"
    + _ANY_QUOTE
    + r"\s+in\s+"
    r"(?P<editor>" + _AUTHOR_LIST + r")"
    r"\s+\((?P<ed_marker>eds?)\),\s+"
    r"(?P<book_title>.+?)"
    r"\s+"
    + _IMPRINT
    + r"(?:\s+(?P<start_page>\d+)"
    + r"(?:\s*,\s*(?P<pinpoint_prefix>(?:pp?\.?\s*|pages?\s+))?"
    + r"(?P<pinpoint>\d+(?:\s*[-–]\s*\d+)?))?)?"
    + r"\s*\.?\s*$",
    regex.UNICODE,
)

# ---- Quick-detection helpers ------------------------------------------------

_IMPRINT_QUICK = regex.compile(
    r"\([^)]+,\s*(?:\d+(?:st|nd|rd|th)\s+ed(?:ition|n)?,\s*)?\d{4}\)",
    regex.UNICODE,
)

_IN_EDITOR = regex.compile(
    r"\bin\s+.+?\s+\(eds?\)",
    regex.UNICODE,
)


class BookParser(BaseCitationParser):
    """Parses book and chapter-in-edited-book citations per AGLC4 Rules 5.2 and 5.3."""

    def can_parse(self, text: str) -> float:
        """Return confidence (0.0-1.0) that this parser can handle this footnote text."""
        text = text.strip().rstrip(".")

        if CHAPTER_PATTERN.search(text):
            return 0.95

        if BOOK_PATTERN.search(text):
            return 0.90

        has_imprint = bool(_IMPRINT_QUICK.search(text))
        has_editor = bool(_IN_EDITOR.search(text))

        if has_imprint and has_editor:
            return 0.7
        if has_imprint:
            return 0.6

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        """Parse the footnote into structured citation fields."""
        text_clean = text.strip()

        m = CHAPTER_PATTERN.search(text_clean)
        if m:
            return self._parse_chapter(m, text_clean, runs)

        m = BOOK_PATTERN.search(text_clean)
        if m:
            return self._parse_book(m, text_clean, runs)

        if _IMPRINT_QUICK.search(text_clean):
            return ParseResult(
                source_type=SourceType.BOOK,
                confidence=0.4,
                fields={
                    "raw_text": text_clean,
                    "is_chapter": False,
                    "parse_error": "could not fully parse book citation",
                },
            )

        return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

    def _parse_book(
        self,
        m: regex.Match,  # type: ignore[type-arg]
        full_text: str,
        runs: list[FootnoteRun],
    ) -> ParseResult:
        """Extract fields from a matched book citation."""
        author = m.group("author").strip()
        title = m.group("title").strip()
        title_quote = m.group("title_quote")
        publisher = m.group("publisher").strip()
        year = m.group("year")
        pinpoint = m.group("pinpoint")
        pinpoint_prefix = m.group("pinpoint_prefix")

        # Fix author-title boundary for surname-first names.
        # When authors are "Surname, Given and Surname2, Given2", the regex
        # captures the last given name as part of the title.
        # e.g., author="Creyke, Robin and Groves", title="Matthew, Control of..."
        # Detect: title starts with "CapWord, " and author has comma (surname-first).
        author, title = self._fix_surname_first_boundary(author, title)

        edition_num: str | None = None
        edition_word: str | None = None
        has_edition_error = False
        if m.group("edition_raw"):
            edition_num = m.group("edition_num")
            edition_word = m.group("edition_word")
            has_edition_error = edition_word != "ed"

        if pinpoint:
            pinpoint = pinpoint.strip()
        has_pinpoint_prefix = pinpoint_prefix is not None and pinpoint_prefix.strip() != ""
        has_double_quotes = title_quote in _DOUBLE_QUOTES

        edition_str: str | None = None
        if edition_num:
            edition_str = f"{edition_num} ed"

        title_is_italic = _check_italic(runs, title)

        # Rule 4.1.1: detect initials with periods (e.g. "H.L.A." should be "HLA")
        has_initial_periods = bool(regex.search(r"\b[A-Z]\.", author))

        # Rule 5.1/5.2: detect surname-first author order
        has_surname_first = self._detect_surname_first(author)

        return ParseResult(
            source_type=SourceType.BOOK,
            confidence=0.90,
            fields={
                "author": author,
                "title": title,
                "publisher": publisher,
                "edition": edition_str,
                "edition_raw": m.group("edition_raw") if m.group("edition_raw") else None,
                "year": year,
                "pinpoint": pinpoint,
                "is_chapter": False,
                "chapter_title": None,
                "editor": None,
                "has_edition_error": has_edition_error,
                "has_double_quotes": has_double_quotes,
                "has_pinpoint_prefix": has_pinpoint_prefix,
                "title_is_italic": title_is_italic,
                "has_initial_periods": has_initial_periods,
                "has_surname_first": has_surname_first,
            },
        )

    def _parse_chapter(
        self,
        m: regex.Match,  # type: ignore[type-arg]
        full_text: str,
        runs: list[FootnoteRun],
    ) -> ParseResult:
        """Extract fields from a matched chapter-in-edited-book citation."""
        author = m.group("author").strip()
        chapter_title = m.group("chapter_title").strip()
        chapter_quote = m.group("chapter_quote")
        editor = m.group("editor").strip()
        ed_marker = m.group("ed_marker")
        book_title = m.group("book_title").strip()
        publisher = m.group("publisher").strip()
        year = m.group("year")
        start_page = m.group("start_page")
        pinpoint = m.group("pinpoint")
        pinpoint_prefix = m.group("pinpoint_prefix")

        edition_num: str | None = None
        edition_word: str | None = None
        has_edition_error = False
        if m.group("edition_raw"):
            edition_num = m.group("edition_num")
            edition_word = m.group("edition_word")
            has_edition_error = edition_word != "ed"

        if pinpoint:
            pinpoint = pinpoint.strip()
        if start_page:
            start_page = start_page.strip()
        has_pinpoint_prefix = pinpoint_prefix is not None and pinpoint_prefix.strip() != ""

        has_double_quotes = chapter_quote in _DOUBLE_QUOTES

        edition_str: str | None = None
        if edition_num:
            edition_str = f"{edition_num} ed"

        book_title_is_italic = _check_italic(runs, book_title)

        # Rule 4.1.1: detect initials with periods (e.g. "H.L.A." should be "HLA")
        has_initial_periods = bool(regex.search(r"\b[A-Z]\.", author))

        # Rule 5.1/5.2: detect surname-first author order
        has_surname_first = self._detect_surname_first(author)

        return ParseResult(
            source_type=SourceType.CHAPTER,
            confidence=0.95,
            fields={
                "author": author,
                "title": book_title,
                "chapter_title": chapter_title,
                "editor": editor,
                "ed_marker": ed_marker,
                "publisher": publisher,
                "edition": edition_str,
                "edition_raw": m.group("edition_raw") if m.group("edition_raw") else None,
                "year": year,
                "start_page": start_page,
                "pinpoint": pinpoint,
                "is_chapter": True,
                "has_edition_error": has_edition_error,
                "has_double_quotes": has_double_quotes,
                "has_pinpoint_prefix": has_pinpoint_prefix,
                "book_title_is_italic": book_title_is_italic,
                "has_initial_periods": has_initial_periods,
                "has_surname_first": has_surname_first,
            },
        )

    @staticmethod
    def _fix_surname_first_boundary(author: str, title: str) -> tuple[str, str]:
        """Fix author-title boundary when surname-first names confuse the regex.

        When authors use "Surname, Given and Surname2, Given2" format, the book
        pattern's _AUTHOR_LIST regex sometimes captures the last given name as
        the start of the title.

        e.g., author="Creyke, Robin and Groves", title="Matthew, Control of..."
        Fix → author="Creyke, Robin and Groves, Matthew", title="Control of..."
        """
        # Only apply if the author contains a comma (suggesting surname-first)
        if "," not in author:
            return author, title

        # Check if title starts with "CapWord, " — likely a given name that belongs
        # to the last author in the list
        m = regex.match(
            r"^([\p{Lu}][\p{L}'''-]+(?:\s+[\p{Lu}][\p{L}'''-]+)*),\s+",
            title,
            regex.UNICODE,
        )
        if not m:
            return author, title

        possible_given = m.group(1)

        # Validate: the last word of author should look like a surname
        # (not a given name that already completes a "Surname, Given" pair)
        author_parts = regex.split(r"\s+and\s+", author)
        last_part = author_parts[-1].strip()

        # If the last part already has a comma (complete "Surname, Given"), no fix needed
        if "," in last_part:
            return author, title

        # The last part is just a surname missing its given name — move it from title
        author_fixed = f"{author}, {possible_given}"
        title_fixed = title[m.end():].strip()

        return author_fixed, title_fixed

    @staticmethod
    def _detect_surname_first(author: str) -> bool:
        """Detect if any author is in 'Surname, Given' format."""
        parts = regex.split(r"\s+and\s+", author)
        for part in parts:
            part = part.strip()
            if regex.match(
                r"^[\p{Lu}][\p{L}'''-]+,\s+[\p{Lu}][\p{L}'''-]+",
                part,
                regex.UNICODE,
            ):
                return True
        return False


def _check_italic(runs: list[FootnoteRun], needle: str) -> bool:
    """Return True if *needle* appears within an italic run."""
    for run in runs:
        if run.italic and needle in run.text:
            return True
    return False
