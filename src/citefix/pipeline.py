"""Pipeline orchestrator — the single public entry point for CiteFix."""

from __future__ import annotations

import logging
from pathlib import Path

from citefix.classifier import Classifier
from citefix.engine.ai_fallback import ai_check_footnote, should_use_ai
from citefix.extractor import extract_footnotes
from citefix.models import Footnote, FootnoteRun, FixResult, Issue, ParseResult, SourceType
from citefix.rewriter import Rewriter
from citefix.rules.cross_ref import check_cross_references
from citefix.rules.engine import RuleEngine
from citefix.signals import strip_introductory_signal

logger = logging.getLogger(__name__)


def process(docx_input: bytes | Path, *, use_ai: bool = False) -> FixResult:
    """Process a .docx file through the full CiteFix pipeline.

    Args:
        docx_input: Raw .docx bytes or path to a .docx file.
        use_ai: If True, use LLM API fallback for low-confidence footnotes.

    Returns:
        FixResult with the corrected .docx and all issues found/fixed/flagged.
    """
    if isinstance(docx_input, Path):  # noqa: SIM108
        docx_bytes = docx_input.read_bytes()
    else:
        docx_bytes = docx_input

    footnotes = extract_footnotes(docx_bytes)

    if not footnotes:
        logger.info("No footnotes found — returning original document")
        return FixResult(
            fixed_docx=docx_bytes,
            footnote_count=0,
            error_count=0,
        )

    classifier = Classifier()
    rule_engine = RuleEngine()
    rewriter = Rewriter()

    parse_results: dict[int, ParseResult] = {}
    all_issues: list[Issue] = []

    for fn in footnotes:
        source_type, confidence, parser = classifier.classify(fn)

        # Composite footnotes: split on semicolons, process each part separately
        if source_type == SourceType.COMPOSITE:
            _process_composite(fn, classifier, rule_engine, parse_results, all_issues)
            continue

        # Strip introductory signals before parsing so they are not included
        # in citation fields like party names or author names (AGLC4 Rule 1.2).
        signal, stripped_text = strip_introductory_signal(fn.plain_text)

        if parser and confidence >= 0.3:
            parse_result = parser.parse(stripped_text, fn.runs)
            # If the parser returned UNKNOWN but the classifier was confident,
            # preserve the classifier's source type (e.g., supra/op cit → SUBSEQUENT_REF)
            if parse_result.source_type == SourceType.UNKNOWN and confidence >= 0.7:
                parse_result = ParseResult(
                    source_type=source_type,
                    confidence=confidence,
                    fields=parse_result.fields,
                )
        else:
            parse_result = ParseResult(
                source_type=source_type,
                confidence=confidence,
            )

        # Attach signal info to every parse result so validators can access it.
        if signal:
            parse_result.fields["signal"] = signal
            parse_result.fields["has_signal"] = True
        else:
            parse_result.fields.setdefault("has_signal", False)
            parse_result.fields.setdefault("signal", "")

        parse_results[fn.index] = parse_result

        if confidence < 0.7 and source_type not in (SourceType.IBID, SourceType.SUBSEQUENT_REF):
            all_issues.append(Issue(
                footnote_index=fn.index,
                rule="classification",
                description=(
                    f"Low confidence classification ({confidence:.0%})"
                    " — needs manual review"
                ),
                current=fn.plain_text[:80],
                suggested="",
                severity="warning",
                auto_fixable=False,
            ))

        issues = rule_engine.validate(fn, parse_result)
        all_issues.extend(issues)

        # Optional AI fallback for footnotes the rule engine cannot confidently fix
        if use_ai and should_use_ai(confidence, issues, fn.plain_text):
            corrected = ai_check_footnote(
                fn.plain_text,
                source_type=source_type.value,
                confidence=confidence,
            )
            if corrected != fn.plain_text:
                logger.info(
                    "AI corrected footnote %d: %.60s → %.60s",
                    fn.index,
                    fn.plain_text,
                    corrected,
                )

    cross_ref_issues = check_cross_references(footnotes, parse_results)
    all_issues.extend(cross_ref_issues)

    fixed_docx = rewriter.apply_fixes(docx_bytes, footnotes, all_issues)

    issues_fixed = [i for i in all_issues if i.auto_fixable]
    issues_flagged = [i for i in all_issues if not i.auto_fixable]

    logger.info(
        "Processed %d footnotes: %d issues found, %d auto-fixed, %d flagged",
        len(footnotes),
        len(all_issues),
        len(issues_fixed),
        len(issues_flagged),
    )

    return FixResult(
        fixed_docx=fixed_docx,
        issues_found=all_issues,
        issues_fixed=issues_fixed,
        issues_flagged=issues_flagged,
        footnote_count=len(footnotes),
        error_count=len(all_issues),
    )


def _process_composite(
    fn: Footnote,
    classifier: Classifier,
    rule_engine: RuleEngine,
    parse_results: dict[int, ParseResult],
    all_issues: list[Issue],
) -> None:
    """Process a composite footnote by splitting on semicolons.

    Each part is classified, parsed, and validated independently.
    Issues are generated with text-replacement targets that work on the
    composite footnote's full text.
    """
    text = fn.plain_text

    # Strip the introductory signal from the whole footnote first
    signal, stripped = strip_introductory_signal(text)

    parts = [p.strip() for p in stripped.split(";")]

    # Store composite parse result for cross-ref tracking
    parse_results[fn.index] = ParseResult(
        source_type=SourceType.COMPOSITE,
        confidence=0.8,
        fields={"part_count": len(parts)},
    )

    for part in parts:
        if not part or len(part) < 5:
            continue

        # Create a synthetic footnote for this part to run through classification
        part_fn = Footnote(
            index=fn.index,
            runs=[FootnoteRun(text=part)],
            xml_element=fn.xml_element,
        )

        part_type, part_conf, part_parser = classifier.classify(part_fn)

        if part_parser and part_conf >= 0.3:
            part_signal, part_stripped = strip_introductory_signal(part)
            part_result = part_parser.parse(part_stripped, part_fn.runs)
        else:
            part_result = ParseResult(
                source_type=part_type,
                confidence=part_conf,
            )

        # Run validators on this part
        part_issues = rule_engine.validate(part_fn, part_result)
        all_issues.extend(part_issues)
