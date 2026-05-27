# CiteFix — Architecture

## Pipeline Design

```
                        ┌─────────────┐
                        │  api.py     │  FastAPI endpoint
                        │  POST /fix  │  accepts .docx, returns fixed .docx
                        └──────┬──────┘
                               │
                               ▼
                        ┌─────────────┐
                        │ pipeline.py │  Orchestrator — the only public entry point
                        └──────┬──────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌──────────────┐  ┌────────────┐  ┌──────────────┐
     │ extractor.py │  │            │  │ rewriter.py  │
     │              │  │ CORE LOOP  │  │              │
     │ .docx → list │  │ for each   │  │ list[Fix] →  │
     │ [Footnote]   │  │ footnote:  │  │ fixed .docx  │
     └──────────────┘  │            │  └──────────────┘
                       │ classify() │
                       │ parse()    │
                       │ validate() │
                       │ → Issues   │
                       └────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌──────────┐ ┌──────────┐ ┌──────────────┐
        │ parsers/ │ │ rules/   │ │ rules/       │
        │          │ │          │ │              │
        │ case.py  │ │engine.py │ │ cross_ref.py │
        │ legis.py │ │validators│ │ (Ibid, n X)  │
        │ journal  │ │          │ │              │
        │ book.py  │ │          │ │              │
        └──────────┘ └──────────┘ └──────────────┘
```

## Data Models

```python
@dataclass
class FootnoteRun:
    """A 'run' is a segment of text with uniform formatting."""
    text: str
    italic: bool = False
    bold: bool = False

@dataclass
class Footnote:
    """A single extracted footnote."""
    index: int                    # Footnote number (1-based)
    runs: list[FootnoteRun]      # Preserves formatting
    plain_text: str               # Flattened text for parsing
    xml_element: etree.Element    # Raw XML reference for rewriting

class SourceType(Enum):
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
    COMPOSITE = "composite"       # Multiple sources in one footnote
    UNKNOWN = "unknown"

@dataclass
class ParseResult:
    """Output of a parser — structured citation fields."""
    source_type: SourceType
    confidence: float             # 0.0–1.0
    fields: dict[str, Any]        # Type-specific fields
    # Case: {parties, year, volume, report_series, start_page, pinpoint, ...}
    # Legislation: {title, year, jurisdiction, pinpoint_type, pinpoint, ...}

@dataclass
class Issue:
    """A single AGLC4 error found in a footnote."""
    footnote_index: int
    rule: str                     # e.g., "2.2.3" or "bracket_type"
    description: str              # Human-readable: "CLR uses round brackets, not square"
    current: str                  # What's there now
    suggested: str                # What it should be
    severity: Literal["error", "warning", "info"]
    auto_fixable: bool            # Can CiteFix fix this automatically?

@dataclass
class FixResult:
    """Final output of the pipeline."""
    fixed_docx: bytes             # The corrected .docx file
    issues_found: list[Issue]     # All issues detected
    issues_fixed: list[Issue]     # Issues that were auto-fixed
    issues_flagged: list[Issue]   # Issues needing manual review
    footnote_count: int
    error_count: int
```

## Parser Pattern

Every parser follows the same interface:

```python
class BaseCitationParser(ABC):
    @abstractmethod
    def can_parse(self, text: str) -> float:
        """Return confidence (0.0–1.0) that this parser handles this text."""

    @abstractmethod
    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        """Parse the footnote text into structured fields."""
```

The classifier calls `can_parse()` on all parsers, picks the highest confidence, and delegates.

## Rewriter Strategy

The rewriter NEVER rebuilds footnotes from scratch. It makes surgical edits to the existing XML:

1. **Italic fixes**: wrap/unwrap `<w:rPr><w:i/></w:rPr>` around runs
2. **Text substitutions**: find "vs" → replace with "v", find "[1992]" → replace with "(1992)"
3. **Append full stop**: add ". " run at end if missing
4. **Ibid replacement**: replace entire footnote content with "Ibid" or "Ibid 55."

This preserves all non-footnote content, styles, headers, images, tables — everything.

## Error Handling

- Parser can't classify → `SourceType.UNKNOWN`, `confidence=0.0`, flagged for manual review
- Parser partially matches → low confidence → flag uncertain fields
- Rewriter encounters unexpected XML structure → skip that footnote, log warning
- API receives non-.docx file → 400 error with clear message
- API receives password-protected .docx → 400 error with message
