"""Cross-footnote reference checker — Ibid and subsequent reference detection."""

from __future__ import annotations

import logging

import regex

from citefix.models import Footnote, Issue, ParseResult, SourceType

logger = logging.getLogger(__name__)


def _normalise_citation(text: str) -> str:
    """Normalise a citation for comparison (strip pinpoints, trailing period, whitespace).

    Also normalises common error variants so FN4 "Palmer versus Ayres (2017) HCA 5"
    matches FN28 "Palmer v Ayres [2017] HCA 5" despite formatting differences.
    """
    text = text.strip().rstrip(".")
    # Strip trailing section-style pinpoint: "s 180(1)", "Section 180(1)", "§ 14" etc.
    text = regex.sub(
        r"[,\s]+(s|ss|reg|regs|r|rr|cl|cll|pt|div|sch|para"
        r"|section|Section|sec\.?|§"
        r"|regulation|Regulation)\s*"
        r"\d+(?:\([a-zA-Z0-9]+\))*(?:\s*[-–]\s*\d+(?:\([a-zA-Z0-9]+\))*)?\s*$",
        "",
        text,
    )
    # Strip trailing page/paragraph-style pinpoint in various formats:
    #   ", 42"  /  ", [31]"  /  "at p. 42"  /  "at page 42"  /  "at 42"  /  "pp. 5-25"
    #   "at paragraph 31"  /  "at para 31"
    text = regex.sub(
        r"(?:,\s*|\s+at\s+)(?:(?:p|pp)\.?\s+|pages?\s+|para(?:graph)?\.?\s+)?"
        r"\[?\d+\]?(?:\s*[-–]\s*\[?\d+\]?)?\s*$",
        "",
        text,
    )
    # Normalise "versus", "vs", "vs.", "V" to "v" for case name comparison
    text = regex.sub(r"\s+(vs\.?|versus|V)\s+", " v ", text, flags=regex.IGNORECASE)
    # Normalise "v." (v with period) to "v"
    text = regex.sub(r"\bv\.\s+", "v ", text)
    # Normalise "No." to "No"
    text = regex.sub(r"\bNo\.\s*", "No ", text)
    # Normalise year brackets: both (2017) and [2017] → 2017
    text = regex.sub(r"[\(\[]\s*(\d{4})\s*[\)\]]", r"\1", text)
    # Normalise section abbreviation variants: "Section", "sec.", "§" → "s"
    text = regex.sub(r"\b(?:section|sec\.?|§)\s*", "s ", text, flags=regex.IGNORECASE)
    # Strip commas before section (", s" → " s")
    text = regex.sub(r",\s+s\b", " s", text)
    # Normalise regulation abbreviations
    text = regex.sub(r"\b(?:regulation|Regulation)\s+", "reg ", text, flags=regex.IGNORECASE)
    text = regex.sub(r"\s+", " ", text)
    return text.lower()


def _extract_pinpoint(text: str) -> str | None:
    """Extract pinpoint from end of citation text.

    Handles both page-style pinpoints (", 42") and section-style pinpoints
    ("s 180(1)") for legislation.
    """
    # Match section-style pinpoint: "s 180(1)", "Section 180(1)", "§14(1)" etc.
    sec_m = regex.search(
        r"\b(s|ss|reg|regs|r|rr|cl|cll|pt|div|sch|para"
        r"|section|Section|sec\.?|§"
        r"|regulation|Regulation)\s*"
        r"(\d+(?:\([a-zA-Z0-9]+\))*(?:\s*[-–]\s*\d+(?:\([a-zA-Z0-9]+\))*)?)\s*\.?\s*$",
        text,
    )
    if sec_m:
        # Normalise the abbreviation to standard AGLC4 form
        abbrev = sec_m.group(1).lower().rstrip(".")
        norm_map = {"section": "s", "sec": "s", "§": "s", "regulation": "reg"}
        abbrev = norm_map.get(abbrev, abbrev)
        return f"{abbrev} {sec_m.group(2)}"

    # Match page/paragraph-style pinpoint: ", 42" or "at p. 42" or ", [31]"
    m = regex.search(
        r"(?:,\s*|\s+at\s+)(?:(?:p|pp)\.?\s+|pages?\s+)?(\[?\d+\]?(?:\s*[-–]\s*\[?\d+\]?)?)\s*\.?\s*$",
        text,
    )
    if m:
        return m.group(1).strip()
    return None


def check_cross_references(
    footnotes: list[Footnote],
    parse_results: dict[int, ParseResult],
) -> list[Issue]:
    """Check all footnotes for Ibid and subsequent reference opportunities.

    Args:
        footnotes: All footnotes in document order.
        parse_results: Mapping of footnote index to its ParseResult.

    Returns:
        List of issues for missing Ibid or subsequent references.
    """
    issues: list[Issue] = []

    # Check for wrong Ibid usage (not consecutive, or in first footnote)
    for i, fn in enumerate(footnotes):
        pr = parse_results.get(fn.index)
        if not pr or pr.source_type != SourceType.IBID:
            continue
        if i == 0:
            issues.append(Issue(
                footnote_index=fn.index,
                rule="1.4.1",
                description="Ibid cannot be used in the first footnote",
                current=fn.plain_text,
                suggested="Full citation required",
                severity="error",
                auto_fixable=False,
            ))

    if len(footnotes) < 2:
        return issues

    normalised: dict[int, str] = {}
    for fn in footnotes:
        pr = parse_results.get(fn.index)
        if pr and pr.source_type not in (SourceType.IBID, SourceType.SUBSEQUENT_REF,
                                          SourceType.COMPOSITE, SourceType.UNKNOWN):
            normalised[fn.index] = _normalise_citation(fn.plain_text)

    first_occurrence: dict[str, int] = {}
    for fn in footnotes:
        norm = normalised.get(fn.index)
        if norm and norm not in first_occurrence:
            first_occurrence[norm] = fn.index

    # Track the "effective" source for each footnote position, so Ibid chains work.
    # When a footnote is detected as Ibid-eligible, the effective source for that
    # position becomes the SAME as the previous one (enabling chains: FN1→FN2→FN3
    # all consecutive same-source can ALL become Ibid, not just the first pair).
    effective_norm: dict[int, str] = {}

    for i in range(len(footnotes)):
        fn = footnotes[i]
        norm = normalised.get(fn.index)
        pr = parse_results.get(fn.index)

        if pr and pr.source_type == SourceType.IBID:
            # Already an Ibid — propagate the previous footnote's effective source
            if i > 0:
                effective_norm[fn.index] = effective_norm.get(footnotes[i - 1].index, "")
        elif norm:
            effective_norm[fn.index] = norm

    for i in range(1, len(footnotes)):
        current = footnotes[i]
        previous = footnotes[i - 1]

        current_pr = parse_results.get(current.index)
        if current_pr and current_pr.source_type in (SourceType.IBID, SourceType.SUBSEQUENT_REF):
            continue

        current_norm = normalised.get(current.index)
        previous_eff = effective_norm.get(previous.index)

        if current_norm and previous_eff and current_norm == previous_eff:
            current_pin = _extract_pinpoint(current.plain_text)
            previous_pin = _extract_pinpoint(previous.plain_text)

            if current_pin and current_pin != previous_pin:
                suggested = f"Ibid {current_pin}."
            else:
                suggested = "Ibid."

            issues.append(Issue(
                footnote_index=current.index,
                rule="1.4.1",
                description="Consecutive same-source citation should use Ibid",
                current=current.plain_text,
                suggested=suggested,
                severity="error",
                auto_fixable=True,
            ))

            # Propagate: this footnote is now effectively Ibid, so the next one
            # in the chain can also detect same-source consecutive.
            effective_norm[current.index] = current_norm
            continue

        if current_norm and current_norm in first_occurrence:
            first_fn = first_occurrence[current_norm]
            if first_fn != current.index:
                current_pin = _extract_pinpoint(current.plain_text)
                current_pr = parse_results.get(current.index)
                short_title = _make_short_title(current.plain_text, current_pr)

                suggested = f"{short_title} (n {first_fn})"
                if current_pin:
                    suggested += f" {current_pin}"
                suggested += "."

                issues.append(Issue(
                    footnote_index=current.index,
                    rule="1.4.2",
                    description="Repeated citation should use subsequent reference format",
                    current=current.plain_text,
                    suggested=suggested,
                    severity="error",
                    auto_fixable=True,
                ))

    # Resolve "op cit" footnotes — find the matching author in earlier footnotes.
    # e.g., "McCutcheon, op cit, 920." → find FN with author "McCutcheon" → "McCutcheon (n X) 920."
    _resolve_op_cit(footnotes, parse_results, issues)

    return issues


def _resolve_op_cit(
    footnotes: list[Footnote],
    parse_results: dict[int, ParseResult],
    issues: list[Issue],
) -> None:
    """Resolve 'op cit' references by matching author surname to earlier footnotes."""
    op_cit_pattern = regex.compile(
        r"^(.+?),?\s+op\.?\s*cit\.?(?:,?\s*(?:at\s+)?(\d+))?\s*\.?\s*$",
        regex.IGNORECASE,
    )

    # Build a map of author surnames → footnote index from earlier parsed footnotes
    author_fn_map: dict[str, int] = {}
    for fn in footnotes:
        pr = parse_results.get(fn.index)
        if not pr:
            continue
        if pr.source_type in (SourceType.JOURNAL_ARTICLE, SourceType.BOOK, SourceType.CHAPTER):
            author = pr.fields.get("author", "")
            if author:
                # Extract surname: last word if "First Last", first word if "Last, First"
                if "," in author:
                    surname = author.split(",")[0].strip()
                else:
                    parts = author.strip().split()
                    surname = parts[-1] if parts else ""
                if surname and surname not in author_fn_map:
                    author_fn_map[surname] = fn.index

    for fn in footnotes:
        pr = parse_results.get(fn.index)
        if not pr or pr.source_type not in (SourceType.SUBSEQUENT_REF, SourceType.UNKNOWN):
            continue

        text = fn.plain_text.strip()
        m = op_cit_pattern.match(text)
        if not m:
            continue

        short_title = m.group(1).strip().rstrip(",")
        pinpoint = m.group(2)

        # Try to match the short_title (author surname) to an earlier footnote
        matched_fn = author_fn_map.get(short_title)

        if matched_fn and matched_fn < fn.index:
            suggested = f"{short_title} (n {matched_fn})"
            if pinpoint:
                suggested += f" {pinpoint}"
            suggested += "."
            issues.append(Issue(
                footnote_index=fn.index,
                rule="1.4.2",
                description="Use '(n X)' format not 'op cit' (AGLC4 Rule 1.4.2)",
                current=text.rstrip("."),
                suggested=suggested,
                severity="error",
                auto_fixable=True,
            ))
        else:
            # Can't find matching author — flag for manual review
            suggested = f"{short_title} (n ?)"
            if pinpoint:
                suggested += f" {pinpoint}"
            suggested += "."
            issues.append(Issue(
                footnote_index=fn.index,
                rule="1.4.2",
                description="Use '(n X)' format not 'op cit' — could not determine footnote number",
                current=text.rstrip("."),
                suggested=suggested,
                severity="error",
                auto_fixable=False,
            ))


def _make_short_title(plain_text: str, parse_result: ParseResult | None) -> str:
    """Generate a short title for subsequent references.

    Cases: first party name (e.g., "Mabo v Queensland" → "Mabo")
    Legislation: short act name (e.g., "Corporations Act 2001 (Cth)" → "Corporations Act")
    Secondary: author surname (e.g., "Jani McCutcheon, ..." → "McCutcheon")
    """
    if parse_result:
        st = parse_result.source_type

        if st == SourceType.CASE:
            parties = parse_result.fields.get("parties", "")
            if parties:
                # First party name only
                first_party = regex.split(r"\s+v\s+", parties, flags=regex.IGNORECASE)[0].strip()
                # If multi-word, just use first meaningful word
                words = first_party.split()
                return words[0] if words else "?"

        if st == SourceType.LEGISLATION:
            title = parse_result.fields.get("title", "")
            if title:
                # Drop generic words at end, keep the distinctive part
                # "Corporations Act" → "Corporations Act"
                # "Fair Work Act" → "Fair Work Act"
                return title

        if st in (SourceType.JOURNAL_ARTICLE, SourceType.BOOK, SourceType.CHAPTER):
            author = parse_result.fields.get("author", "")
            if author:
                # Extract surname (last word, or word before comma)
                if "," in author:
                    return author.split(",")[0].strip()
                parts = author.strip().split()
                return parts[-1] if parts else "?"

    # Fallback: first word of plain text
    parts = plain_text.strip().split()
    return parts[0] if parts else "?"
