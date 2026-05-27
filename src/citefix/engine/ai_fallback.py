"""Optional AI fallback -- send ambiguous footnotes to an LLM API for classification.

When the rule-based classifier returns confidence < 0.7, the pipeline can optionally
hand the citation to an LLM for a best-effort classification.  This module is entirely
optional: if the ``anthropic`` package is not installed or ``ANTHROPIC_API_KEY`` is not
set, every public method degrades gracefully (returns UNKNOWN / empty list).

The module also provides standalone helper functions (``ai_check_footnote`` and
``should_use_ai``) for use by the pipeline when the ``use_ai`` flag is enabled.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from citefix.models import FootnoteRun, ParseResult, SourceType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 4096
_TIMEOUT_SECONDS = 30
_MIN_REQUEST_INTERVAL = 0.25  # crude rate-limiter: at most 4 req/s

# Map the lowercase source-type labels the LLM returns back to our enum.
_SOURCE_TYPE_MAP: dict[str, SourceType] = {
    "case": SourceType.CASE,
    "legislation": SourceType.LEGISLATION,
    "journal_article": SourceType.JOURNAL_ARTICLE,
    "book": SourceType.BOOK,
    "chapter": SourceType.CHAPTER,
    "report": SourceType.REPORT,
    "website": SourceType.WEBSITE,
    "treaty": SourceType.TREATY,
    "hansard": SourceType.HANSARD,
}

# ---------------------------------------------------------------------------
# System prompt (cached across calls via prompt caching)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert in the Australian Guide to Legal Citation, 4th edition (AGLC4).

Your task is to classify legal citation footnotes and extract structured fields.

Each citation belongs to exactly ONE of these source types:
  case, legislation, journal_article, book, chapter, report, website, treaty, hansard

Return your answer as a JSON object (no markdown fences, no commentary):

{
  "source_type": "<one of the types above>",
  "confidence": <0.0-1.0>,
  "fields": { ... }
}

Field schemas per source type:

CASE
  parties (str) -- full case name, e.g. "Mabo v Queensland (No 2)"
  year (str) -- e.g. "1992"
  volume (str|null) -- e.g. "175"
  report_series (str) -- e.g. "CLR"
  start_page (str) -- e.g. "1"
  pinpoint (str|null) -- e.g. "42"
  court (str|null) -- e.g. "HCA" for medium-neutral

LEGISLATION
  title (str) -- e.g. "Corporations Act"
  year (str) -- e.g. "2001"
  jurisdiction (str) -- e.g. "Cth"
  pinpoint_type (str|null) -- e.g. "s", "reg", "sch"
  pinpoint (str|null) -- e.g. "180(1)"

JOURNAL_ARTICLE
  author (str) -- e.g. "Jani McCutcheon"
  title (str) -- article title without quotes
  year (str)
  volume (str|null)
  journal (str) -- full journal name
  start_page (str)
  pinpoint (str|null)

BOOK
  author (str)
  title (str)
  publisher (str|null)
  edition (str|null) -- e.g. "2nd ed"
  year (str)
  pinpoint (str|null)

CHAPTER
  author (str)
  chapter_title (str)
  editor (str)
  book_title (str)
  publisher (str|null)
  edition (str|null)
  year (str)
  start_page (str|null)
  pinpoint (str|null)

REPORT
  author_or_body (str) -- e.g. "Australian Law Reform Commission"
  title (str)
  report_number (str|null) -- e.g. "Report No 133"
  year (str)
  pinpoint (str|null)

WEBSITE
  author (str|null)
  title (str)
  website_name (str|null)
  date (str|null)
  url (str|null)

TREATY
  title (str)
  date_signed (str|null)
  treaty_series (str|null)
  entry_into_force (str|null)

HANSARD
  jurisdiction (str)
  chamber (str|null)
  date (str)
  pinpoint (str|null)
  speaker (str|null)

AGLC4 citation format examples for reference:

Case (reported):
  Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.

Case (medium-neutral):
  Palmer v Ayres [2017] HCA 5, [31].

Legislation:
  Corporations Act 2001 (Cth) s 180(1).

Journal article:
  Jani McCutcheon, 'The Vanishing Author in Computer-Generated Works' (2013) 36 \
University of New South Wales Law Journal 915.

Book:
  Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) 45.

Chapter in edited book:
  Andrew Stewart, 'The Evolution of Labour Law' in Andrew Stewart et al (eds), \
Creighton and Stewart's Labour Law (Federation Press, 6th ed, 2016) 1, 15.

Report:
  Australian Law Reform Commission, Traditional Rights and Freedoms: \
Encroachments by Commonwealth Laws (Report No 129, 2015).

Website:
  Sarah Moulds, 'Parliamentary Scrutiny Explained' on Australian Public Law \
(Blog Post, 3 March 2021) <https://auspublaw.org/blog/2021/03/scrutiny-explained>.

Treaty:
  Convention on the Rights of the Child, opened for signature 20 November 1989, \
1577 UNTS 3 (entered into force 2 September 1990).

Hansard:
  Commonwealth, Parliamentary Debates, Senate, 11 October 2017, 7834 (George Brandis).

If you cannot determine the source type, return:
{"source_type": "unknown", "confidence": 0.0, "fields": {}}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runs_to_annotated_text(runs: list[FootnoteRun]) -> str:
    """Convert runs to a text representation that preserves formatting hints.

    Italic segments are wrapped in ``*...*`` so the LLM can see where italics are,
    which is essential for distinguishing case names, legislation titles, etc.
    """
    parts: list[str] = []
    for run in runs:
        if run.italic:
            parts.append(f"*{run.text}*")
        elif run.bold:
            parts.append(f"**{run.text}**")
        else:
            parts.append(run.text)
    return "".join(parts)


def _parse_response_json(raw: str) -> dict[str, Any]:
    """Best-effort extraction of JSON from the LLM's response text.

    The LLM almost always returns clean JSON, but occasionally wraps it in
    a markdown code fence.  Strip that if present.
    """
    text = raw.strip()
    # Strip optional ```json ... ``` wrapper
    if text.startswith("```"):
        # Remove opening fence line
        first_newline = text.index("\n")
        text = text[first_newline + 1 :]
        # Remove closing fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()[: -len("```")]
    return json.loads(text)  # type: ignore[no-any-return]


def _json_to_parse_result(data: dict[str, Any]) -> ParseResult:
    """Convert a validated JSON dict into a ``ParseResult``."""
    raw_type = str(data.get("source_type", "unknown")).lower()
    source_type = _SOURCE_TYPE_MAP.get(raw_type, SourceType.UNKNOWN)
    confidence = float(data.get("confidence", 0.0))
    # Clamp to [0, 1]
    confidence = max(0.0, min(1.0, confidence))
    fields: dict[str, Any] = data.get("fields", {})
    if not isinstance(fields, dict):
        fields = {}
    return ParseResult(source_type=source_type, confidence=confidence, fields=fields)


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------


class AIFallback:
    """Uses an LLM API to classify ambiguous citations.

    Only activated when ``ANTHROPIC_API_KEY`` is set in the environment **and**
    the ``anthropic`` Python package is installed.  When neither condition is
    met every method returns a safe default so the rest of the pipeline is
    unaffected.
    """

    def __init__(self) -> None:
        self._api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")
        self._client: Any = None
        self._last_request_time: float = 0.0

        if self._api_key:
            try:
                import anthropic

                self._client = anthropic.Anthropic(
                    api_key=self._api_key,
                    timeout=_TIMEOUT_SECONDS,
                )
            except ImportError:
                logger.warning(
                    "anthropic package not installed -- AI fallback disabled"
                )

    # -- properties ----------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True when the AI fallback can actually make API calls."""
        return self._client is not None

    # -- rate-limiting -------------------------------------------------------

    def _wait_for_rate_limit(self) -> None:
        """Sleep briefly if we are sending requests faster than the limit."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    # -- single classification -----------------------------------------------

    def classify(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        """Send an ambiguous citation to the LLM for classification.

        Args:
            text: Plain text of the footnote.
            runs: Formatted runs (preserves italic/bold info).

        Returns:
            A ``ParseResult`` with the AI's best guess at source type and
            fields.  Falls back to ``UNKNOWN`` with confidence 0.0 if the
            API call fails or the client is unavailable.
        """
        if not self.is_available:
            return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

        annotated = _runs_to_annotated_text(runs)
        user_message = (
            f"Classify this AGLC4 footnote citation and extract structured fields.\n\n"
            f"Plain text: {text}\n"
            f"Formatted (italic marked with *): {annotated}\n\n"
            f"Return JSON only."
        )

        try:
            self._wait_for_rate_limit()
            response = self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text: str = response.content[0].text
            data = _parse_response_json(raw_text)
            result = _json_to_parse_result(data)
            logger.info(
                "AI classified citation as %s (confidence %.2f): %.60s",
                result.source_type.value,
                result.confidence,
                text,
            )
            return result

        except json.JSONDecodeError:
            logger.warning("AI returned unparseable JSON for citation: %.80s", text)
            return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)
        except Exception:
            logger.exception("AI fallback failed for citation: %.80s", text)
            return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

    # -- batch classification ------------------------------------------------

    def batch_classify(
        self,
        items: list[tuple[str, list[FootnoteRun]]],
    ) -> list[ParseResult]:
        """Classify multiple ambiguous citations in a single API call.

        Sends all citations in one user message and asks the LLM to return a
        JSON array.  This is much more efficient than individual calls when
        there are many ambiguous footnotes in a document.

        Args:
            items: List of ``(plain_text, runs)`` tuples.

        Returns:
            A list of ``ParseResult`` objects, one per input item.  On
            failure the list contains ``UNKNOWN`` results for every item.
        """
        if not items:
            return []

        unknown = ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

        if not self.is_available:
            return [unknown] * len(items)

        # Build the user prompt with numbered citations
        citation_lines: list[str] = []
        for idx, (text, runs) in enumerate(items, start=1):
            annotated = _runs_to_annotated_text(runs)
            citation_lines.append(
                f"[{idx}] Plain: {text}\n    Formatted: {annotated}"
            )
        numbered_block = "\n\n".join(citation_lines)

        user_message = (
            f"Classify each of the following {len(items)} AGLC4 footnote citations "
            f"and extract structured fields for each one.\n\n"
            f"{numbered_block}\n\n"
            f"Return a JSON array of {len(items)} objects, one per citation, in the "
            f"same order.  Each object has the schema: "
            f'{{"source_type": "...", "confidence": 0.0-1.0, "fields": {{...}}}}.\n'
            f"Return JSON only, no commentary."
        )

        try:
            self._wait_for_rate_limit()
            response = self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_message}],
            )
            raw_text: str = response.content[0].text
            data = _parse_response_json(raw_text)

            if not isinstance(data, list):
                logger.warning(
                    "AI batch response is not a JSON array; falling back to UNKNOWN"
                )
                return [unknown] * len(items)

            results: list[ParseResult] = []
            for entry in data:
                if isinstance(entry, dict):
                    results.append(_json_to_parse_result(entry))
                else:
                    results.append(unknown)

            # Pad or trim if the LLM returned wrong count
            while len(results) < len(items):
                results.append(unknown)
            results = results[: len(items)]

            logger.info("AI batch-classified %d citations", len(items))
            return results

        except json.JSONDecodeError:
            logger.warning(
                "AI returned unparseable JSON for batch of %d citations",
                len(items),
            )
            return [unknown] * len(items)
        except Exception:
            logger.exception(
                "AI fallback failed for batch of %d citations", len(items)
            )
            return [unknown] * len(items)


# ---------------------------------------------------------------------------
# Standalone helper functions for pipeline use_ai mode
# ---------------------------------------------------------------------------

_CORRECTION_SYSTEM_PROMPT = """\
You are an AGLC4 citation formatter. You receive a single Australian legal footnote \
that may contain formatting errors. Return ONLY the corrected footnote text — no \
explanation, no markdown, no quotes around it.

AGLC4 rules you must follow:
- Cases: Case Name (Year) Volume Report StartPage, Pinpoint. Case name fully italicised. \
"v" lowercase.
- Round brackets for year in reported series (CLR, FCR, NSWLR, ALR, ALJR, WAR, VR, SASR, \
Qd R, Tas R, ACTLR, NTLR, FLR).
- Square brackets for year in medium-neutral citations (HCA, FCA, FCAFC, NSWSC, NSWCA, \
WASC, WASCA, VSC, VSCA, QSC, QCA, SASC, TASSC, ACTSC, NTSC).
- Legislation: Title Year (Jurisdiction) pinpoint. Title and year italicised. Jurisdiction \
NOT italic. Title comes FIRST, pinpoint LAST.
- Section abbreviated: s (not Section, sec, or section sign). Space after s: "s 14" not \
"s14". No comma before s.
- Jurisdiction abbreviated: (Cth), (NSW), (Vic), (Qld), (WA), (SA), (Tas), (ACT), (NT).
- Pinpoints: bare number after comma. No "p.", "at", "page". En-dash for ranges.
- Journal articles: Author, 'Title' (Year) Vol Journal Name Page, Pinpoint. Single quotes. \
Full journal name.
- Books: Author, Title (Publisher, Xth ed, Year) Pinpoint. "ed" not "edition".
- Ibid: capitalised, italicised, for immediately preceding same source only.
- Subsequent references: ShortTitle (n X) Pinpoint.
- Every footnote ends with a full stop.
- Australian Constitution: cite as Australian Constitution s X — no jurisdiction, no year.\
"""


def ai_check_footnote(
    footnote_text: str,
    source_type: str = "unknown",
    confidence: float = 0.0,
) -> str:
    """Send a footnote to the LLM for correction.

    Only call this for footnotes where the rule engine has low confidence
    or detected structural issues it cannot fix deterministically.

    Args:
        footnote_text: The raw (or partially-fixed) footnote text.
        source_type: What the classifier thinks it is.
        confidence: The parser's confidence score (0.0-1.0).

    Returns:
        The corrected footnote text, or the original if the API call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.debug("No ANTHROPIC_API_KEY set, skipping AI fallback")
        return footnote_text

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=_CORRECTION_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"Source type detected: {source_type} (confidence: {confidence:.1f})\n"
                    f"Footnote: {footnote_text}\n"
                    f"Corrected:"
                ),
            }],
        )
        corrected = response.content[0].text.strip()

        # Safety: if the LLM returns something wildly different, keep original
        if len(corrected) > len(footnote_text) * 3 or len(corrected) < 5:
            logger.warning("AI response too different from input, keeping original")
            return footnote_text

        return corrected
    except ImportError:
        logger.warning("anthropic package not installed, skipping AI fallback")
        return footnote_text
    except Exception as e:
        logger.error("AI fallback failed: %s", e)
        return footnote_text


def should_use_ai(confidence: float, issues: list, text: str) -> bool:  # noqa: ANN001
    """Decide whether a footnote needs the AI fallback.

    Returns True if:
    - Parser confidence is below 0.7
    - Section-before-title was detected but reordering was not confident
    - Footnote has 3+ unresolved (non-auto-fixable) issues
    """
    if confidence < 0.7:
        return True

    # Check for wrong citation style indicators
    wrong_style_indicators = [
        "v.", "C.L.R.", "F.C.R.", "H.C.A.", "Id.", "supra",
        "supra note", "infra", "op cit", "loc cit",
        "above n", "(note ", "https://doi.org", "Retrieved from",
    ]
    for indicator in wrong_style_indicators:
        if indicator in text:
            return True

    # Too many unfixable issues
    unfixable = [i for i in issues if not i.auto_fixable]
    if len(unfixable) >= 3:
        return True

    return False
