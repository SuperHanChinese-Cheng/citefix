"""Rule engine — runs all validators on parsed citations."""

from __future__ import annotations

import logging

from citefix.models import Footnote, Issue, ParseResult
from citefix.rules.validators import (
    validate_above_n_reference,
    validate_author_name_order,
    validate_book_title_italics,
    validate_book_title_quotes,
    validate_case_name_italics,
    validate_case_name_quotes,
    validate_case_v_separator,
    validate_comma_before_year,
    validate_double_quotes,
    validate_double_spacing,
    validate_duplicate_year_brackets,
    validate_edition_abbreviation,
    validate_full_stop,
    validate_ibid_format,
    validate_initial_periods,
    validate_journal_abbreviation,
    validate_journal_italics,
    validate_journal_the_prefix,
    validate_jurisdiction_format,
    validate_legislation_italics,
    validate_medium_neutral_pinpoint,
    validate_no_period,
    validate_non_aglc4_reference,
    validate_note_x_reference,
    validate_pinpoint_comma,
    validate_pinpoint_format,
    validate_pinpoint_prefix,
    validate_report_series_periods,
    validate_section_abbreviation,
    validate_section_before_title,
    validate_section_spacing,
    validate_year_brackets,
)

logger = logging.getLogger(__name__)


class RuleEngine:
    """Runs all AGLC4 validators against a parsed footnote."""

    def validate(self, footnote: Footnote, parse_result: ParseResult) -> list[Issue]:
        """Run all applicable validators and return all issues found."""
        issues: list[Issue] = []

        full_stop = validate_full_stop(footnote)
        if full_stop:
            issues.append(full_stop)

        issues.extend(validate_pinpoint_format(footnote, parse_result))

        v_sep = validate_case_v_separator(footnote, parse_result)
        if v_sep:
            issues.append(v_sep)

        bracket = validate_year_brackets(footnote, parse_result)
        if bracket:
            issues.append(bracket)

        case_italic = validate_case_name_italics(footnote, parse_result)
        if case_italic:
            issues.append(case_italic)

        legis_italic = validate_legislation_italics(footnote, parse_result)
        if legis_italic:
            issues.append(legis_italic)

        issues.extend(validate_section_abbreviation(footnote, parse_result))

        issues.extend(validate_jurisdiction_format(footnote, parse_result))

        sec_spacing = validate_section_spacing(footnote, parse_result)
        if sec_spacing:
            issues.append(sec_spacing)

        non_aglc4 = validate_non_aglc4_reference(footnote, parse_result)
        if non_aglc4:
            issues.append(non_aglc4)

        mn_pinpoint = validate_medium_neutral_pinpoint(footnote, parse_result)
        if mn_pinpoint:
            issues.append(mn_pinpoint)

        pin_comma = validate_pinpoint_comma(footnote, parse_result)
        if pin_comma:
            issues.append(pin_comma)

        dq = validate_double_quotes(footnote, parse_result)
        if dq:
            issues.append(dq)

        issues.extend(validate_edition_abbreviation(footnote, parse_result))

        issues.extend(validate_author_name_order(footnote, parse_result))

        pin_prefix = validate_pinpoint_prefix(footnote, parse_result)
        if pin_prefix:
            issues.append(pin_prefix)

        issues.extend(validate_ibid_format(footnote, parse_result))

        init_periods = validate_initial_periods(footnote, parse_result)
        if init_periods:
            issues.append(init_periods)

        the_prefix = validate_journal_the_prefix(footnote, parse_result)
        if the_prefix:
            issues.append(the_prefix)

        # Journal italic MUST run before abbreviation so the italic fix finds the
        # original text. After italic wraps the abbreviated name in an italic run,
        # the abbreviation fix replaces it in-place (inheriting the italic formatting).
        journal_italic = validate_journal_italics(footnote, parse_result)
        if journal_italic:
            issues.append(journal_italic)

        journal_abbrev = validate_journal_abbreviation(footnote, parse_result)
        if journal_abbrev:
            issues.append(journal_abbrev)

        book_quotes = validate_book_title_quotes(footnote, parse_result)
        if book_quotes:
            issues.append(book_quotes)

        book_italic = validate_book_title_italics(footnote, parse_result)
        if book_italic:
            issues.append(book_italic)

        double_space = validate_double_spacing(footnote)
        if double_space:
            issues.append(double_space)

        no_period = validate_no_period(footnote, parse_result)
        if no_period:
            issues.append(no_period)

        report_periods = validate_report_series_periods(footnote, parse_result)
        if report_periods:
            issues.append(report_periods)

        comma_year = validate_comma_before_year(footnote, parse_result)
        if comma_year:
            issues.append(comma_year)

        case_quotes = validate_case_name_quotes(footnote, parse_result)
        if case_quotes:
            issues.append(case_quotes)

        above_n = validate_above_n_reference(footnote, parse_result)
        if above_n:
            issues.append(above_n)

        note_x = validate_note_x_reference(footnote, parse_result)
        if note_x:
            issues.append(note_x)

        dup_year = validate_duplicate_year_brackets(footnote, parse_result)
        if dup_year:
            issues.append(dup_year)

        sec_before = validate_section_before_title(footnote, parse_result)
        if sec_before:
            issues.append(sec_before)

        logger.debug(
            "Footnote %d: %d issues found",
            footnote.index,
            len(issues),
        )
        return issues
