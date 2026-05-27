"""Base citation parser interface."""

from abc import ABC, abstractmethod

from citefix.models import FootnoteRun, ParseResult


class BaseCitationParser(ABC):
    """Abstract base class for all citation parsers.

    Each parser handles one source type (cases, legislation, journal articles, etc.).
    The classifier calls can_parse() on all parsers and delegates to the highest-confidence match.
    """

    @abstractmethod
    def can_parse(self, text: str) -> float:
        """Return confidence (0.0–1.0) that this parser can handle this footnote text.

        Args:
            text: Plain text of the footnote (formatting stripped).

        Returns:
            Confidence score. 0.0 = definitely not this type. 1.0 = certain match.
        """
        ...

    @abstractmethod
    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        """Parse the footnote into structured citation fields.

        Args:
            text: Plain text of the footnote.
            runs: Formatted runs (preserves italic/bold info for validation).

        Returns:
            ParseResult with source_type, confidence, and extracted fields.
        """
        ...
