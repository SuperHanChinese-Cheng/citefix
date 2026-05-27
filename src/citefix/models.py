"""Core data models for CiteFix."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from lxml import etree


class SourceType(Enum):
    """Classification of a footnote's source type."""

    CASE = "case"
    LEGISLATION = "legislation"
    JOURNAL_ARTICLE = "journal_article"
    BOOK = "book"
    CHAPTER = "chapter"
    REPORT = "report"
    WEBSITE = "website"
    TREATY = "treaty"
    HANSARD = "hansard"
    IBID = "ibid"
    SUBSEQUENT_REF = "subsequent_ref"
    COMPOSITE = "composite"
    UNKNOWN = "unknown"


@dataclass
class FootnoteRun:
    """A run is a contiguous segment of text with uniform formatting.

    A single footnote is composed of multiple runs. For example:
    '*Mabo v Queensland*' is one italic run, ' (1992) 175 CLR 1.' is a non-italic run.
    """

    text: str
    italic: bool = False
    bold: bool = False


@dataclass
class Footnote:
    """A single extracted footnote from a .docx file."""

    index: int  # 1-based footnote number
    runs: list[FootnoteRun] = field(default_factory=list)
    xml_element: etree._Element | None = None  # Raw XML for rewriting

    @property
    def plain_text(self) -> str:
        """Flatten all runs into a single string for parsing."""
        return "".join(run.text for run in self.runs).strip()

    @property
    def has_italic_content(self) -> bool:
        """Check if any run in this footnote is italicised."""
        return any(run.italic for run in self.runs)


@dataclass
class ParseResult:
    """Output of a citation parser — structured fields extracted from a footnote."""

    source_type: SourceType
    confidence: float  # 0.0–1.0
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass
class Issue:
    """A single AGLC4 error detected in a footnote."""

    footnote_index: int
    rule: str  # AGLC4 rule reference, e.g., "2.2.3"
    description: str  # Human-readable explanation
    current: str  # What the footnote currently has
    suggested: str  # What it should be
    severity: Literal["error", "warning", "info"] = "error"
    auto_fixable: bool = True


@dataclass
class FixResult:
    """Final output of the CiteFix pipeline."""

    fixed_docx: bytes  # The corrected .docx file
    issues_found: list[Issue] = field(default_factory=list)
    issues_fixed: list[Issue] = field(default_factory=list)
    issues_flagged: list[Issue] = field(default_factory=list)  # Needs manual review
    footnote_count: int = 0
    error_count: int = 0
