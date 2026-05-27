"""Individual AGLC4 validation functions."""

from __future__ import annotations

import regex

from citefix.models import Footnote, Issue, ParseResult, SourceType
from citefix.rules.abbreviations import BracketType, get_bracket_type, is_medium_neutral


def validate_full_stop(footnote: Footnote) -> Issue | None:
    """Rule 1.1: Every footnote must end with a full stop."""
    text = footnote.plain_text
    if not text.endswith("."):
        return Issue(
            footnote_index=footnote.index,
            rule="1.1",
            description="Footnote must end with a full stop",
            current=text[-10:] if len(text) > 10 else text,
            suggested=text + ".",
            severity="error",
        )
    return None


def validate_pinpoint_format(footnote: Footnote, parse_result: ParseResult) -> list[Issue]:
    """Rule 1.3: No 'p.', 'at', 'page' in pinpoints."""
    issues: list[Issue] = []
    text = footnote.plain_text
    is_mn = parse_result.fields.get("is_medium_neutral", False)
    is_book = parse_result.source_type in (SourceType.BOOK, SourceType.CHAPTER)

    # Skip "at/p./page" prefix check for books — handled by validate_pinpoint_prefix instead
    # Books use "Author, Title (Publisher, ed, Year) Pinpoint." (space, no comma)
    if not is_book:
        # Capture leading whitespace/comma to prevent " ," or ", ," artifacts
        at_p_pattern = regex.compile(
            r"[\s,]+(at\s+(?:(?:p|pp)\.?\s*|pages?\s+|paras?\s+|paragraphs?\s+)?|(?:p|pp)\.?\s+|pages?\s+|paras?\s+|paragraphs?\s+)(\d+(?:\s*[-–—]\s*\d+)?)",
            regex.UNICODE,
        )
        for m in at_p_pattern.finditer(text):
            num_str = m.group(2)
            if is_mn:
                # Medium-neutral citations: wrap numbers in square brackets, use en-dash
                parts = regex.split(r"\s*[-–]\s*", num_str)
                if len(parts) == 2:
                    suggested = f", [{parts[0]}]–[{parts[1]}]"
                else:
                    suggested = f", [{num_str}]"
            else:
                suggested = f", {num_str}"
            issues.append(Issue(
                footnote_index=footnote.index,
                rule="1.3",
                description="Pinpoint references should not use 'at', 'p.', or 'page'",
                current=m.group(0),
                suggested=suggested,
                severity="error",
            ))

    hyphen_range = regex.compile(r"(\d+)\s*-\s*(\d+)")
    for m in hyphen_range.finditer(text):
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="1.3",
            description="Use en-dash (–) not hyphen (-) for page ranges",
            current=m.group(0),
            suggested=f"{m.group(1)}–{m.group(2)}",
            severity="error",
        ))

    # Detect em-dash (U+2014) in ranges — should be en-dash (U+2013)
    emdash_range = regex.compile(r"(\d+)\s*—\s*(\d+)")
    for m in emdash_range.finditer(text):
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="1.3",
            description="Use en-dash (–) not em-dash (—) for page ranges",
            current=m.group(0),
            suggested=f"{m.group(1)}–{m.group(2)}",
            severity="error",
            auto_fixable=True,
        ))

    # Detect "vol." or "vol" prefix before volume number
    vol_match = regex.search(r"\bvol\.?\s+\d+", text, regex.IGNORECASE)
    if vol_match:
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="1.3",
            description="Remove 'vol.' prefix from volume number",
            current=vol_match.group(0),
            suggested=regex.sub(r"\bvol\.?\s+", "", vol_match.group(0), flags=regex.IGNORECASE),
            severity="error",
            auto_fixable=True,
        ))

    return issues


def validate_case_v_separator(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.1: Case names must use 'v' not 'vs', 'vs.', or 'versus'."""
    if parse_result.source_type != SourceType.CASE:
        return None
    if not parse_result.fields.get("has_v_error"):
        return None

    parties = parse_result.fields.get("parties", "")
    # Check for "vs", "vs.", "versus" (case-insensitive)
    bad_match = regex.search(r"\s+(vs\.?|versus)\s+", parties, regex.IGNORECASE)
    if not bad_match:
        # Check for uppercase "V" (should be lowercase "v")
        bad_match = regex.search(r"\s+(V)\s+", parties)
    if bad_match:
        return Issue(
            footnote_index=footnote.index,
            rule="2.1",
            description="Case names must use 'v' not 'vs' or 'versus'",
            current=bad_match.group(0).strip(),
            suggested="v",
            severity="error",
        )

    # Check for "v." (v with spurious period)
    v_dot_match = regex.search(r"\s+(v\.)\s+", parties)
    if v_dot_match:
        return Issue(
            footnote_index=footnote.index,
            rule="2.1",
            description="Case names must use 'v' not 'v.'",
            current="v.",
            suggested="v",
            severity="error",
        )

    return None


def validate_year_brackets(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.2: Year brackets must match report series (round vs square)."""
    if parse_result.source_type != SourceType.CASE:
        return None

    report_series = parse_result.fields.get("report_series")
    if not report_series:
        return None

    required = get_bracket_type(report_series)
    if required is None:
        return None

    year = parse_result.fields.get("year", "")
    actual_open = parse_result.fields.get("year_bracket_open", "")

    if required == BracketType.ROUND and actual_open == "[":
        return Issue(
            footnote_index=footnote.index,
            rule="2.2",
            description=f"{report_series} uses round brackets for year, not square",
            current=f"[{year}]",
            suggested=f"({year})",
            severity="error",
        )
    elif required == BracketType.SQUARE and actual_open == "(":
        return Issue(
            footnote_index=footnote.index,
            rule="2.2",
            description=f"{report_series} uses square brackets for year, not round",
            current=f"({year})",
            suggested=f"[{year}]",
            severity="error",
        )
    return None


def validate_case_name_italics(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.1: Case names must be italicised."""
    if parse_result.source_type != SourceType.CASE:
        return None

    parties = parse_result.fields.get("parties", "")
    if not parties:
        return None

    italic_runs = parse_result.fields.get("italic_runs", [])
    italic_text = "".join(r.text for r in italic_runs)

    # Check if parties text appears in italic runs (allowing for "v"/"vs" differences)
    party_parts = regex.split(r"\s+(?:vs?\.?|versus)\s+", parties, flags=regex.IGNORECASE)
    all_parties_italic = all(
        any(part.strip() in italic_text for part in [p])
        for p in party_parts
        if p.strip()
    )

    if not all_parties_italic:
        return Issue(
            footnote_index=footnote.index,
            rule="2.1",
            description="Case name must be italicised",
            current=parties,
            suggested=parties,
            severity="warning",
            auto_fixable=True,
        )
    return None


def validate_legislation_italics(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 3.1: Legislation title and year must be italicised, jurisdiction must NOT be."""
    if parse_result.source_type != SourceType.LEGISLATION:
        return None

    # Skip low-confidence classifications to avoid spurious italic fixes
    # on misclassified footnotes (e.g., journal articles containing "Law 2016")
    if parse_result.confidence < 0.7:
        return None

    if not parse_result.fields.get("title_is_italic"):
        title = parse_result.fields.get("title", "")
        year = parse_result.fields.get("year", "")
        return Issue(
            footnote_index=footnote.index,
            rule="3.1",
            description="Legislation title and year must be italicised",
            current=f"{title} {year}",
            suggested=f"{title} {year}",
            severity="warning",
            auto_fixable=True,
        )

    if parse_result.fields.get("jurisdiction_is_italic"):
        jurisdiction = parse_result.fields.get("jurisdiction", "")
        return Issue(
            footnote_index=footnote.index,
            rule="3.1",
            description="Jurisdiction abbreviation must NOT be italicised",
            current=f"({jurisdiction})",
            suggested=f"({jurisdiction})",
            severity="error",
            auto_fixable=True,
        )

    return None


def validate_section_abbreviation(footnote: Footnote, parse_result: ParseResult) -> list[Issue]:
    """Rule 3.2: Section must be abbreviated to 's', not 'section', 'sec', '§'."""
    issues: list[Issue] = []
    if parse_result.source_type != SourceType.LEGISLATION:
        return issues

    pinpoint_type_error = parse_result.fields.get("pinpoint_type_error")
    if pinpoint_type_error:
        from citefix.rules.jurisdictions import SECTION_ABBREVIATIONS

        correct = SECTION_ABBREVIATIONS.get(pinpoint_type_error, "s")
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="3.2",
            description=f"Use '{correct}' not '{pinpoint_type_error}'",
            current=pinpoint_type_error,
            suggested=correct,
            severity="error",
            auto_fixable=True,
        ))

    if parse_result.fields.get("has_comma_before_pinpoint"):
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="3.2",
            description="No comma between jurisdiction and section pinpoint",
            current=", s",
            suggested=" s",
            severity="error",
            auto_fixable=True,
        ))

    # Handle "s." (abbreviation 's' with spurious period after it)
    text = footnote.plain_text
    if regex.search(r"\bs\.\s*\d+", text):
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="3.2",
            description="Use 's' not 's.' for section abbreviation",
            current="s.",
            suggested="s",
            severity="error",
            auto_fixable=True,
        ))

    return issues


def validate_jurisdiction_format(footnote: Footnote, parse_result: ParseResult) -> list[Issue]:
    """Rule 3.1: Jurisdiction must be abbreviated and in brackets.

    Detects:
    - Full jurisdiction names that should be abbreviated: (Western Australia) → (WA)
    - Bare jurisdiction abbreviations missing brackets: NSW → (NSW)
    - Missing jurisdiction entirely (warning only)
    """
    issues: list[Issue] = []
    if parse_result.source_type != SourceType.LEGISLATION:
        return issues

    jurisdiction_format = parse_result.fields.get("jurisdiction_format")
    jurisdiction_raw = parse_result.fields.get("jurisdiction_raw")
    jurisdiction = parse_result.fields.get("jurisdiction")  # Normalised abbreviation

    if jurisdiction_format == "bracketed" and parse_result.fields.get("jurisdiction_is_full_name"):
        # Full name in brackets: (Western Australia) → (WA)
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="3.1",
            description=f"Use abbreviated jurisdiction '({jurisdiction})' not '({jurisdiction_raw})'",
            current=f"({jurisdiction_raw})",
            suggested=f"({jurisdiction})",
            severity="error",
            auto_fixable=True,
        ))

    elif jurisdiction_format == "bare":
        # Bare abbreviation without brackets: NSW → (NSW)
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="3.1",
            description=f"Jurisdiction must be in brackets: '({jurisdiction})'",
            current=jurisdiction_raw or "",
            suggested=f"({jurisdiction})",
            severity="error",
            auto_fixable=True,
        ))

    elif jurisdiction_format == "missing":
        # No jurisdiction at all — flag as warning (can't auto-fix without knowing jurisdiction)
        title = parse_result.fields.get("title", "")
        year = parse_result.fields.get("year", "")
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="3.1",
            description=f"Jurisdiction is missing for '{title} {year}' — add e.g. (Cth), (NSW)",
            current=f"{title} {year}",
            suggested=f"{title} {year} (Cth)",
            severity="warning",
            auto_fixable=False,
        ))

    return issues


def validate_double_spacing(footnote: Footnote) -> Issue | None:
    """General: No double spaces in footnotes."""
    text = footnote.plain_text
    if "  " in text:
        return Issue(
            footnote_index=footnote.index,
            rule="general",
            description="Remove double spaces",
            current="  ",
            suggested=" ",
            severity="info",
        )
    return None


def validate_double_quotes(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 5.1/5.3: Article and chapter titles use single quotes, not double."""
    if parse_result.source_type not in (SourceType.JOURNAL_ARTICLE, SourceType.CHAPTER):
        return None

    if not parse_result.fields.get("has_double_quotes"):
        return None

    title = parse_result.fields.get("title", "") or parse_result.fields.get("chapter_title", "")
    return Issue(
        footnote_index=footnote.index,
        rule="5.1",
        description="Use single quotes for article/chapter titles, not double quotes",
        current=f'"{title}"',
        suggested=f"'{title}'",
        severity="error",
        auto_fixable=True,
    )


_WORD_ORDINALS: dict[str, str] = {
    "First": "1st", "Second": "2nd", "Third": "3rd", "Fourth": "4th",
    "Fifth": "5th", "Sixth": "6th", "Seventh": "7th", "Eighth": "8th",
    "Ninth": "9th", "Tenth": "10th", "Eleventh": "11th", "Twelfth": "12th",
    "Thirteenth": "13th", "Fourteenth": "14th", "Fifteenth": "15th",
    "Sixteenth": "16th", "Seventeenth": "17th", "Eighteenth": "18th",
    "Nineteenth": "19th", "Twentieth": "20th",
}


def validate_edition_abbreviation(footnote: Footnote, parse_result: ParseResult) -> list[Issue]:
    """Rule 5.2: Use 'ed' not 'edition', 'edn' for edition."""
    issues: list[Issue] = []
    if parse_result.source_type not in (SourceType.BOOK, SourceType.CHAPTER):
        return issues

    if parse_result.fields.get("has_edition_error"):
        edition_raw = parse_result.fields.get("edition_raw", "")
        if edition_raw:
            issues.append(Issue(
                footnote_index=footnote.index,
                rule="5.2",
                description="Use 'ed' not 'edition' or 'edn'",
                current=edition_raw,
                suggested=edition_raw.replace("edition", "ed").replace("edn", "ed"),
                severity="error",
                auto_fixable=True,
            ))

    # Detect word-ordinals before "ed"/"edition"/"edn": "Fifth Edition" → "5th ed"
    text = footnote.plain_text
    ordinal_pattern = regex.compile(
        r"\b(" + "|".join(regex.escape(w) for w in _WORD_ORDINALS) + r")\s+(ed(?:ition|n)?)\b",
        regex.IGNORECASE,
    )
    for m in ordinal_pattern.finditer(text):
        word = m.group(1)
        # Look up the capitalised form
        numeral = _WORD_ORDINALS.get(word) or _WORD_ORDINALS.get(word.capitalize())
        if numeral:
            suffix = m.group(2).lower()
            suggested_suffix = "ed" if suffix in ("edition", "edn") else suffix
            issues.append(Issue(
                footnote_index=footnote.index,
                rule="5.2",
                description=f"Use '{numeral} ed' not '{word} {m.group(2)}'",
                current=m.group(0),
                suggested=f"{numeral} {suggested_suffix}",
                severity="error",
                auto_fixable=True,
            ))

    return issues


def validate_author_name_order(footnote: Footnote, parse_result: ParseResult) -> list[Issue]:
    """Rule 5.1/5.2: Author names should be first-name-then-surname, not surname-first."""
    issues: list[Issue] = []
    if parse_result.source_type not in (SourceType.JOURNAL_ARTICLE, SourceType.BOOK, SourceType.CHAPTER):
        return issues

    author = parse_result.fields.get("author", "")

    # Detect "&" between authors
    if author and "&" in author:
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="4.1",
            description="Use 'and' not '&' between author names",
            current="&",
            suggested="and",
            severity="error",
            auto_fixable=True,
        ))

    if not parse_result.fields.get("has_surname_first"):
        return issues

    # Attempt to compute the swapped name: "McCutcheon, Jani" → "Jani McCutcheon"
    # Handle multiple authors separated by " and " or " & ": "Creyke, Robin and Groves, Matthew"
    fixed_parts = []
    for part in regex.split(r"\s+(?:and|&)\s+", author):
        part = part.strip()
        if "," in part:
            pieces = [p.strip() for p in part.split(",", 1)]
            if len(pieces) == 2 and pieces[1]:
                fixed_parts.append(f"{pieces[1]} {pieces[0]}")
            else:
                fixed_parts.append(part)
        else:
            fixed_parts.append(part)

    suggested = " and ".join(fixed_parts)

    issues.append(Issue(
        footnote_index=footnote.index,
        rule="5.1",
        description="Author name should be first name then surname (not surname first)",
        current=author,
        suggested=suggested,
        severity="error",
        auto_fixable=True,
    ))

    return issues


def validate_pinpoint_prefix(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 5.2: Book pinpoints should not have 'p', 'p.', 'page' prefix."""
    if parse_result.source_type not in (SourceType.BOOK, SourceType.CHAPTER):
        return None

    if not parse_result.fields.get("has_pinpoint_prefix"):
        return None

    pinpoint = parse_result.fields.get("pinpoint", "")
    return Issue(
        footnote_index=footnote.index,
        rule="5.2",
        description="Pinpoint should be just the number, not 'p' or 'page'",
        current=f"p {pinpoint}" if pinpoint else "p ...",
        suggested=pinpoint,
        severity="error",
        auto_fixable=True,
    )


def validate_ibid_format(footnote: Footnote, parse_result: ParseResult) -> list[Issue]:
    """Rule 1.4.1: Ibid must be capitalised, italicised, with full stop."""
    issues: list[Issue] = []
    if parse_result.source_type != SourceType.IBID:
        return issues

    # "Id." / "id." is not AGLC4 — must be "Ibid"
    if parse_result.fields.get("is_id_variant"):
        keyword = parse_result.fields.get("keyword", "Id")
        pinpoint = parse_result.fields.get("pinpoint", "")
        suggested = f"Ibid {pinpoint}." if pinpoint else "Ibid."
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="1.4.1",
            description="Use 'Ibid' not 'Id.' (AGLC4 does not use 'Id.')",
            current=keyword,
            suggested=suggested,
            severity="error",
            auto_fixable=True,
        ))
        # Return early — no need to check capitalisation/italic of "Id."
        # The fix will replace the whole content with proper Ibid.
        return issues

    if not parse_result.fields.get("is_capitalised", True):
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="1.4.1",
            description="'Ibid' must be capitalised",
            current="ibid",
            suggested="Ibid",
            severity="error",
            auto_fixable=True,
        ))

    if not parse_result.fields.get("has_full_stop", True):
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="1.4.1",
            description="Ibid must end with a full stop",
            current=footnote.plain_text,
            suggested=footnote.plain_text.rstrip() + ".",
            severity="error",
            auto_fixable=True,
        ))

    if parse_result.fields.get("has_comma_before_pinpoint"):
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="1.4.1",
            description="Ibid pinpoint should not be preceded by a comma",
            current="Ibid,",
            suggested="Ibid",
            severity="error",
            auto_fixable=True,
        ))

    if not parse_result.fields.get("is_italic", True):
        issues.append(Issue(
            footnote_index=footnote.index,
            rule="1.4.1",
            description="'Ibid' must be italicised",
            current="Ibid",
            suggested="Ibid",
            severity="warning",
            auto_fixable=True,
        ))

    return issues


def validate_non_aglc4_reference(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 1.4: Detect non-AGLC4 reference styles (supra, op cit, above n) and convert.

    - "Mabo, supra note 1, at 42." → "Mabo (n 1) 42."
    - "McCutcheon, op cit, 920." → "McCutcheon (n X) 920."
    """
    if parse_result.source_type not in (SourceType.SUBSEQUENT_REF, SourceType.UNKNOWN):
        return None

    text = footnote.plain_text.strip()

    # Detect "supra note X" or "supra n X"
    supra_match = regex.search(
        r"^(.+?),?\s+supra\s+(?:note|n)\s*(\d+)(?:,?\s*(?:at\s+)?(\d+))?\s*\.?\s*$",
        text,
        regex.IGNORECASE,
    )
    if supra_match:
        short_title = supra_match.group(1).strip().rstrip(",")
        fn_ref = supra_match.group(2)
        pinpoint = supra_match.group(3)
        suggested = f"{short_title} (n {fn_ref})"
        if pinpoint:
            suggested += f" {pinpoint}"
        suggested += "."
        return Issue(
            footnote_index=footnote.index,
            rule="1.4.2",
            description="Use '(n X)' format not 'supra note X' (AGLC4 Rule 1.4.2)",
            current=text.rstrip("."),
            suggested=suggested,
            severity="error",
            auto_fixable=True,
        )

    # Op cit is handled in cross_ref.py where we can resolve the footnote number
    # by scanning earlier footnotes for a matching author surname.

    return None


def validate_medium_neutral_pinpoint(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.3/2.4: Medium-neutral citations use [para] not 'para 31'."""
    if parse_result.source_type != SourceType.CASE:
        return None
    if not parse_result.fields.get("is_medium_neutral"):
        return None

    text = footnote.plain_text

    # Match "para(graph)(s) X" or "at para(graph)(s) X" — capture leading whitespace/comma
    para_match = regex.search(
        r"[\s,]+((?:at\s+)?para(?:graph)?s?\.?\s+)(\d+(?:\s*[-–]\s*\d+)?)",
        text,
        regex.IGNORECASE,
    )
    if para_match:
        num_str = para_match.group(2)
        parts = regex.split(r"\s*[-–]\s*", num_str)
        if len(parts) == 2:
            suggested = f", [{parts[0]}]–[{parts[1]}]"
        else:
            suggested = f", [{num_str}]"
        return Issue(
            footnote_index=footnote.index,
            rule="2.4",
            description="Medium-neutral pinpoints use square brackets, not 'para'",
            current=para_match.group(0),
            suggested=suggested,
            severity="error",
        )

    # Match "at [X]" (has "at" before bracket pinpoint — remove the "at")
    at_bracket = regex.search(r"[\s,]+(at\s+)(\[\d+\])", text, regex.IGNORECASE)
    if at_bracket:
        return Issue(
            footnote_index=footnote.index,
            rule="2.4",
            description="Remove 'at' before bracket pinpoint in medium-neutral citation",
            current=at_bracket.group(0),
            suggested=f", {at_bracket.group(2)}",
            severity="error",
        )

    # Rule 1.1.6: Bare number pinpoint on medium-neutral citation should be in [brackets].
    # e.g., "HCA 5, 31" → "HCA 5, [31]"
    pinpoint = parse_result.fields.get("pinpoint")
    if pinpoint and regex.fullmatch(r"\d+(?:\s*[-–]\s*\d+)?", pinpoint):
        # Pinpoint is a bare number (no brackets) — it should be [X] for paragraph reference
        parts = regex.split(r"\s*[-–]\s*", pinpoint)
        if len(parts) == 2:
            suggested_pin = f"[{parts[0]}]–[{parts[1]}]"
        else:
            suggested_pin = f"[{pinpoint}]"
        return Issue(
            footnote_index=footnote.index,
            rule="1.1.6",
            description="Paragraph pinpoints must be in square brackets for medium-neutral citations",
            current=pinpoint,
            suggested=suggested_pin,
            severity="error",
            auto_fixable=True,
        )

    return None


def validate_section_spacing(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 3.1.4: There must be a space between section abbreviation and number."""
    if parse_result.source_type != SourceType.LEGISLATION:
        return None

    text = footnote.plain_text
    # Match "s180" but not "ss" or "sub-s"
    m = regex.search(r"\b(s|ss|reg|regs|cl|cll|pt|div|sch|para|r|rr)(\d+)", text)
    if m:
        return Issue(
            footnote_index=footnote.index,
            rule="3.2",
            description="Space required between pinpoint abbreviation and number",
            current=m.group(0),
            suggested=f"{m.group(1)} {m.group(2)}",
            severity="error",
            auto_fixable=True,
        )

    # Also catch missing space after § or other symbols (parser detects this)
    if parse_result.fields.get("has_pinpoint_spacing_error"):
        pinpoint_type = parse_result.fields.get("pinpoint_type", "")
        pinpoint = parse_result.fields.get("pinpoint", "")
        if pinpoint_type and pinpoint:
            return Issue(
                footnote_index=footnote.index,
                rule="3.2",
                description="Space required between pinpoint abbreviation and number",
                current=f"{pinpoint_type}{pinpoint}",
                suggested=f"{pinpoint_type} {pinpoint}",
                severity="error",
                auto_fixable=True,
            )

    return None


def validate_pinpoint_comma(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.3: Case pinpoints must be preceded by a comma."""
    if parse_result.source_type != SourceType.CASE:
        return None

    start_page = parse_result.fields.get("start_page")
    pinpoint = parse_result.fields.get("pinpoint")
    if not start_page or not pinpoint:
        return None

    text = footnote.plain_text
    # Look for "start_page pinpoint" with just whitespace (no comma)
    pattern = regex.compile(
        regex.escape(start_page) + r"\s+" + regex.escape(pinpoint) + r"(?=[\s.]|$)"
    )
    m = pattern.search(text)
    if m:
        # Check there's no comma in the match
        if "," not in m.group(0):
            return Issue(
                footnote_index=footnote.index,
                rule="1.3",
                description="Pinpoint must be preceded by a comma",
                current=m.group(0),
                suggested=f"{start_page}, {pinpoint}",
                severity="error",
            )
    return None


def validate_initial_periods(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 4.1.1: Author initials should not have periods or spaces between them.

    E.g. "H.L.A. Hart" should be "HLA Hart", "R. J. Ellicott" should be "RJ Ellicott".
    """
    if parse_result.source_type not in (
        SourceType.JOURNAL_ARTICLE, SourceType.BOOK, SourceType.CHAPTER,
    ):
        return None

    if not parse_result.fields.get("has_initial_periods"):
        return None

    author = parse_result.fields.get("author", "")
    # Step 1: Remove periods after single uppercase letters (initials)
    fixed = regex.sub(r"([A-Z])\.", r"\1", author)
    # Step 2: Collapse spaces between adjacent single capitals (e.g. "H L A" → "HLA")
    fixed = regex.sub(r"(?<=[A-Z]) (?=[A-Z](?:\s|$))", "", fixed)
    if fixed == author:
        return None

    return Issue(
        footnote_index=footnote.index,
        rule="4.1",
        description="Initials should not have full stops or spaces between them",
        current=author,
        suggested=fixed,
        severity="error",
        auto_fixable=True,
    )


def validate_journal_the_prefix(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 5.5: Journal names should not begin with 'the'."""
    if parse_result.source_type != SourceType.JOURNAL_ARTICLE:
        return None

    if not parse_result.fields.get("has_the_prefix"):
        return None

    journal_name = parse_result.fields.get("journal_name", "")
    fixed = regex.sub(r"^[Tt]he\s+", "", journal_name)
    return Issue(
        footnote_index=footnote.index,
        rule="5.5",
        description="Journal name should not begin with 'the'",
        current=journal_name,
        suggested=fixed,
        severity="error",
        auto_fixable=True,
    )


def validate_journal_abbreviation(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 5.1: Journal names must be written in full, not abbreviated."""
    if parse_result.source_type != SourceType.JOURNAL_ARTICLE:
        return None

    if not parse_result.fields.get("has_abbreviated_journal"):
        return None

    from citefix.parsers.journal import JOURNAL_ABBREVIATIONS

    journal_name = parse_result.fields.get("journal_name", "")
    full_name = JOURNAL_ABBREVIATIONS.get(journal_name)
    if not full_name:
        # Unknown abbreviation — flag for manual review
        return Issue(
            footnote_index=footnote.index,
            rule="5.1",
            description=f"Journal name '{journal_name}' appears abbreviated — use full name",
            current=journal_name,
            suggested="",
            severity="warning",
            auto_fixable=False,
        )

    return Issue(
        footnote_index=footnote.index,
        rule="5.1",
        description=f"Use full journal name, not abbreviation",
        current=journal_name,
        suggested=full_name,
        severity="error",
        auto_fixable=True,
    )


def validate_journal_italics(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 5.1: Journal name must be italicised."""
    if parse_result.source_type != SourceType.JOURNAL_ARTICLE:
        return None

    if parse_result.fields.get("journal_is_italic"):
        return None

    journal_name = parse_result.fields.get("journal_name", "")
    if not journal_name:
        return None

    return Issue(
        footnote_index=footnote.index,
        rule="5.1",
        description="Journal name must be italicised",
        current=journal_name,
        suggested=journal_name,
        severity="warning",
        auto_fixable=True,
    )


def validate_book_title_quotes(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 5.2: Book titles should NOT be in quotes (only chapter titles get quotes)."""
    if parse_result.source_type != SourceType.BOOK:
        return None

    if not parse_result.fields.get("has_double_quotes"):
        return None

    title = parse_result.fields.get("title", "")
    return Issue(
        footnote_index=footnote.index,
        rule="5.2",
        description="Book titles should not be in quotes (italicise instead)",
        current=f'"{title}"',
        suggested=title,
        severity="error",
        auto_fixable=True,
    )


def validate_book_title_italics(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 5.2: Book title must be italicised."""
    if parse_result.source_type != SourceType.BOOK:
        return None

    if parse_result.fields.get("title_is_italic"):
        return None

    title = parse_result.fields.get("title", "")
    if not title:
        return None

    return Issue(
        footnote_index=footnote.index,
        rule="5.2",
        description="Book title must be italicised",
        current=title,
        suggested=title,
        severity="warning",
        auto_fixable=True,
    )


def validate_no_period(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.1: Remove period after 'No' in case name (e.g., 'No.' → 'No')."""
    if parse_result.source_type != SourceType.CASE:
        return None

    parties = parse_result.fields.get("parties", "")
    if not parties:
        return None

    if "No." in parties:
        return Issue(
            footnote_index=footnote.index,
            rule="2.1",
            description="Remove period after 'No' in case name",
            current="No.",
            suggested="No",
            severity="error",
            auto_fixable=True,
        )
    return None


def validate_report_series_periods(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.2: Remove periods from report series abbreviation (e.g., 'C.L.R.' → 'CLR')."""
    if parse_result.source_type != SourceType.CASE:
        return None

    text = footnote.plain_text
    m = regex.search(r"([A-Z]\.){2,}", text)
    if m:
        matched = m.group(0)
        suggested = matched.replace(".", "")
        return Issue(
            footnote_index=footnote.index,
            rule="2.2",
            description="Remove periods from report series abbreviation",
            current=matched,
            suggested=suggested,
            severity="error",
            auto_fixable=True,
        )
    return None


def validate_comma_before_year(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.1: Remove comma before year bracket in case name."""
    if parse_result.source_type != SourceType.CASE:
        return None

    text = footnote.plain_text
    m = regex.search(r",\s*[\[\(]\d{4}[\]\)]", text)
    if m:
        matched = m.group(0)
        suggested = regex.sub(r"^,\s*", " ", matched)
        return Issue(
            footnote_index=footnote.index,
            rule="2.1",
            description="Remove comma before year bracket in case name",
            current=matched,
            suggested=suggested,
            severity="error",
            auto_fixable=True,
        )
    return None


def validate_case_name_quotes(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.1: Case names should not be in quotes (use italics)."""
    if parse_result.source_type != SourceType.CASE:
        return None

    text = footnote.plain_text
    m = regex.search(r'["“”](.+?\s+v\s+.+?)["“”]', text)
    if m:
        quoted = m.group(0)
        unquoted = m.group(1)
        return Issue(
            footnote_index=footnote.index,
            rule="2.1",
            description="Case names should not be in quotes (use italics)",
            current=quoted,
            suggested=unquoted,
            severity="error",
            auto_fixable=True,
        )
    return None


def validate_above_n_reference(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 1.4.2: Use '(n X)' format not 'above n X'."""
    if parse_result.source_type not in (SourceType.SUBSEQUENT_REF, SourceType.UNKNOWN):
        return None

    text = footnote.plain_text.strip()
    m = regex.match(
        r"(.+?),?\s+above\s+n(?:ote)?\s+(\d+)(?:,?\s*(.+?))?\s*\.?\s*$",
        text,
        regex.IGNORECASE,
    )
    if m:
        title = m.group(1).strip().rstrip(",")
        num = m.group(2)
        pin = m.group(3)
        suggested = f"{title} (n {num})"
        if pin:
            suggested += f" {pin}"
        suggested += "."
        return Issue(
            footnote_index=footnote.index,
            rule="1.4.2",
            description="Use '(n X)' format not 'above n X' (AGLC4 Rule 1.4.2)",
            current=text.rstrip("."),
            suggested=suggested,
            severity="error",
            auto_fixable=True,
        )
    return None


def validate_note_x_reference(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 1.4.2: Use '(n X)' format not '(note X)'."""
    if parse_result.source_type not in (SourceType.SUBSEQUENT_REF, SourceType.UNKNOWN):
        return None

    text = footnote.plain_text.strip()
    m = regex.match(
        r"(.+?)\s+\(note\s+(\d+)\)\s*,?\s*(.+?)?\s*\.?\s*$",
        text,
        regex.IGNORECASE,
    )
    if m:
        title = m.group(1).strip()
        num = m.group(2)
        pin = m.group(3)
        suggested = f"{title} (n {num})"
        if pin:
            suggested += f" {pin}"
        suggested += "."
        return Issue(
            footnote_index=footnote.index,
            rule="1.4.2",
            description="Use '(n X)' format not '(note X)' (AGLC4 Rule 1.4.2)",
            current=text.rstrip("."),
            suggested=suggested,
            severity="error",
            auto_fixable=True,
        )
    return None


def validate_duplicate_year_brackets(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Rule 2.2: Remove duplicate year bracket in case citations."""
    if parse_result.source_type != SourceType.CASE:
        return None

    text = footnote.plain_text
    m = regex.search(r"([\[\(])(\d{4})([\]\)])\s*([\[\(])(\d{4})([\]\)])", text)
    if m:
        report_series = parse_result.fields.get("report_series", "")
        bracket_type = get_bracket_type(report_series)

        if bracket_type == BracketType.ROUND:
            correct_open, correct_close = "(", ")"
        elif bracket_type == BracketType.SQUARE:
            correct_open, correct_close = "[", "]"
        else:
            correct_open, correct_close = "[", "]"

        year = m.group(2) if m.group(2) == m.group(5) else m.group(5)
        return Issue(
            footnote_index=footnote.index,
            rule="2.2",
            description="Remove duplicate year bracket",
            current=m.group(0),
            suggested=f"{correct_open}{year}{correct_close}",
            severity="error",
            auto_fixable=True,
        )
    return None


def detect_section_before_title(text: str) -> bool:
    """Detect 's 31A Federal Court of Australia Act 1976 (Cth)' pattern.

    AGLC4 requires: Title Year (Jurisdiction) pinpoint
    NOT: pinpoint Title Year (Jurisdiction)
    """
    pattern = (
        r'\b(s|ss|reg|regs|r|rr|cl|pt|div|sch)\s+\d+\S*'
        r'\s+'
        r'[A-Z][A-Za-z\s]+?'
        r'\b(Act|Acts|Rules|Regulations?|Code|Ordinance|Law|Bill)\b'
        r'\s+\d{4}'
    )
    return bool(regex.search(pattern, text))


def reorder_section_after_title(text: str) -> str:
    """Move section pinpoint from before the title to after the jurisdiction.

    Input:  's 31A Federal Court of Australia Act 1976 (Cth)'
    Output: 'Federal Court of Australia Act 1976 (Cth) s 31A'
    """
    pattern = (
        r'\b((?:s|ss|reg|regs|r|rr|cl|pt|div|sch)\s+\d+\S*)'
        r'\s+'
        r'((?:[A-Z][A-Za-z\s]+?)'
        r'(?:Act|Acts|Rules|Regulations?|Code|Ordinance|Law|Bill)'
        r'\s+\d{4})'
        r'(\s*\([A-Za-z]+\))?'
    )
    match = regex.search(pattern, text)
    if match:
        section = match.group(1)
        title_year = match.group(2)
        jurisdiction = match.group(3) or ""
        replacement = f"{title_year.strip()}{jurisdiction} {section}"
        text = text[:match.start()] + replacement + text[match.end():]
    return text


def validate_section_before_title(footnote: Footnote, parse_result: ParseResult) -> Issue | None:
    """Detect section pinpoint appearing before legislation title."""
    if parse_result.source_type not in (SourceType.LEGISLATION, SourceType.COMPOSITE, SourceType.UNKNOWN):
        return None

    text = footnote.plain_text
    if not detect_section_before_title(text):
        return None

    corrected = reorder_section_after_title(text)
    return Issue(
        footnote_index=footnote.index,
        rule="3.1",
        description="Section pinpoint must appear after title and jurisdiction, not before",
        current=text,
        suggested=corrected,
        severity="error",
        auto_fixable=True,
    )
