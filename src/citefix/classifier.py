"""Step 2: Classify footnotes into source types using regex patterns."""

from __future__ import annotations

import logging

import regex

from citefix.models import Footnote, SourceType
from citefix.parsers.base import BaseCitationParser
from citefix.parsers.book import BookParser
from citefix.parsers.case import CaseCitationParser
from citefix.parsers.ibid import IbidParser, SubsequentRefParser
from citefix.parsers.journal import JournalArticleParser
from citefix.parsers.legislation import LegislationParser
from citefix.parsers.report import ReportParser
from citefix.parsers.treaty import TreatyParser
from citefix.parsers.website import WebsiteParser
from citefix.signals import strip_introductory_signal
from citefix.text_utils import normalize_text

logger = logging.getLogger(__name__)

# Quick-match for Ibid-like citations including "Id." variant
# Also handles "Id. at 55." and "Ibid, at p. 42."
IBID_PATTERN = regex.compile(
    r"^\s*(?:[Ii]bid|[Ii]d)\.?"
    r"(?:\s*,?\s*(?:at\s+)?(?:(?:p|pp)\.?\s+)?\[?\d+\]?)?"
    r"\.?\s*$",
    regex.UNICODE,
)

SUBSEQUENT_REF_PATTERN = regex.compile(
    r"\(n\s*\d+\)",
    regex.UNICODE,
)

# Non-AGLC4 reference styles: "supra note X", "op cit", "above n X"
SUPRA_PATTERN = regex.compile(
    r"supra\s+(?:note|n)\s*(\d+)",
    regex.UNICODE | regex.IGNORECASE,
)

OP_CIT_PATTERN = regex.compile(
    r"op\.?\s*cit",
    regex.UNICODE | regex.IGNORECASE,
)


class Classifier:
    """Classifies footnotes by source type using registered parsers."""

    def __init__(self) -> None:
        self._ibid_parser = IbidParser()
        self._subseq_parser = SubsequentRefParser()
        self._parsers: list[BaseCitationParser] = [
            self._ibid_parser,
            self._subseq_parser,
            CaseCitationParser(),
            LegislationParser(),
            JournalArticleParser(),
            BookParser(),
            ReportParser(),
            WebsiteParser(),
            TreatyParser(),
        ]

    def classify(self, footnote: Footnote) -> tuple[SourceType, float, BaseCitationParser | None]:
        """Classify a footnote and return the best-matching source type.

        Returns:
            Tuple of (source_type, confidence, parser_or_none).
        """
        text = normalize_text(footnote.plain_text)

        if IBID_PATTERN.match(text):
            return SourceType.IBID, 1.0, self._ibid_parser

        if SUBSEQUENT_REF_PATTERN.search(text):
            return SourceType.SUBSEQUENT_REF, 0.9, self._subseq_parser

        # Non-AGLC4 reference styles → classify as SUBSEQUENT_REF for fix-up
        if SUPRA_PATTERN.search(text):
            return SourceType.SUBSEQUENT_REF, 0.85, self._subseq_parser

        if OP_CIT_PATTERN.search(text):
            return SourceType.SUBSEQUENT_REF, 0.80, self._subseq_parser

        if ";" in text:
            parts = [p.strip() for p in text.split(";")]
            if len(parts) >= 2 and all(len(p) > 10 for p in parts):
                return SourceType.COMPOSITE, 0.8, None

        # Strip introductory signals ("See", "See also", "Cf", etc.) so they
        # don't pollute parser classification (AGLC4 Rule 1.2).
        _signal, stripped_text = strip_introductory_signal(text)

        best_parser: BaseCitationParser | None = None
        best_confidence = 0.0

        for parser in self._parsers:
            confidence = parser.can_parse(stripped_text)
            if confidence > best_confidence:
                best_confidence = confidence
                best_parser = parser

        if best_parser is None or best_confidence < 0.3:
            logger.debug("Could not classify footnote %d: '%s'", footnote.index, text[:80])
            return SourceType.UNKNOWN, 0.0, None

        source_type = best_parser.parse(stripped_text, footnote.runs).source_type
        return source_type, best_confidence, best_parser
