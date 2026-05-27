"""Tests for AGLC4 validators."""

from __future__ import annotations

from citefix.models import FootnoteRun, ParseResult, SourceType
from citefix.rules.validators import (
    validate_case_name_italics,
    validate_case_v_separator,
    validate_double_spacing,
    validate_full_stop,
    validate_ibid_format,
    validate_initial_periods,
    validate_journal_the_prefix,
    validate_jurisdiction_format,
    validate_legislation_italics,
    validate_medium_neutral_pinpoint,
    validate_pinpoint_comma,
    validate_pinpoint_format,
    validate_section_abbreviation,
    validate_section_spacing,
    validate_year_brackets,
)
from tests.conftest import make_footnote


class TestFullStop:
    def test_missing_full_stop(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1, 42")
        issue = validate_full_stop(fn)
        assert issue is not None
        assert issue.rule == "1.1"

    def test_has_full_stop(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1, 42.")
        assert validate_full_stop(fn) is None


class TestPinpointFormat:
    def test_at_p(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1 at p. 42.")
        pr = ParseResult(source_type=SourceType.CASE, confidence=0.9)
        issues = validate_pinpoint_format(fn, pr)
        assert any("at" in i.description or "p." in i.description for i in issues)

    def test_page_word(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1 at page 42.")
        pr = ParseResult(source_type=SourceType.CASE, confidence=0.9)
        issues = validate_pinpoint_format(fn, pr)
        assert len(issues) >= 1

    def test_hyphen_range(self) -> None:
        fn = make_footnote(1, "Palmer v Ayres (2017) 259 CLR 478, 487-490.")
        pr = ParseResult(source_type=SourceType.CASE, confidence=0.9)
        issues = validate_pinpoint_format(fn, pr)
        assert any("en-dash" in i.description for i in issues)

    def test_correct_pinpoint_no_issues(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1, 42.")
        pr = ParseResult(source_type=SourceType.CASE, confidence=0.9)
        issues = validate_pinpoint_format(fn, pr)
        assert len(issues) == 0


class TestVSeparator:
    def test_vs_error(self) -> None:
        fn = make_footnote(1, "Mabo vs Queensland (1992) 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"has_v_error": True, "parties": "Mabo vs Queensland"},
        )
        issue = validate_case_v_separator(fn, pr)
        assert issue is not None
        assert issue.suggested == "v"

    def test_correct_v(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"has_v_error": False, "parties": "Mabo v Queensland"},
        )
        assert validate_case_v_separator(fn, pr) is None


class TestYearBrackets:
    def test_clr_needs_round_has_square(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland [1992] 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={
                "report_series": "CLR",
                "year": "1992",
                "year_bracket_open": "[",
            },
        )
        issue = validate_year_brackets(fn, pr)
        assert issue is not None
        assert issue.suggested == "(1992)"

    def test_hca_needs_square_has_round(self) -> None:
        fn = make_footnote(1, "Palmer v Ayres (2017) HCA 5.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={
                "report_series": "HCA",
                "year": "2017",
                "year_bracket_open": "(",
            },
        )
        issue = validate_year_brackets(fn, pr)
        assert issue is not None
        assert issue.suggested == "[2017]"

    def test_correct_brackets_no_issue(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={
                "report_series": "CLR",
                "year": "1992",
                "year_bracket_open": "(",
            },
        )
        assert validate_year_brackets(fn, pr) is None

    def test_qd_r_needs_square_has_round(self) -> None:
        """Qd R (Queensland Reports) is year-organised — requires square brackets."""
        fn = make_footnote(1, "King v King (1974) Qd R 253.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={
                "report_series": "Qd R",
                "year": "1974",
                "year_bracket_open": "(",
            },
        )
        issue = validate_year_brackets(fn, pr)
        assert issue is not None
        assert issue.suggested == "[1974]"

    def test_qd_r_correct_square_brackets(self) -> None:
        """Qd R with correct square brackets should not produce an issue."""
        fn = make_footnote(1, "King v King [1974] Qd R 253.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={
                "report_series": "Qd R",
                "year": "1974",
                "year_bracket_open": "[",
            },
        )
        assert validate_year_brackets(fn, pr) is None


class TestSectionAbbreviation:
    def test_section_spelled_out(self) -> None:
        fn = make_footnote(1, "Corporations Act 2001 (Cth) Section 180.")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
            fields={"pinpoint_type_error": "Section", "has_comma_before_pinpoint": False},
        )
        issues = validate_section_abbreviation(fn, pr)
        assert any(i.suggested == "s" for i in issues)

    def test_comma_before_section(self) -> None:
        fn = make_footnote(1, "Corporations Act 2001 (Cth), s 180.")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
            fields={"pinpoint_type_error": None, "has_comma_before_pinpoint": True},
        )
        issues = validate_section_abbreviation(fn, pr)
        assert any("comma" in i.description.lower() for i in issues)

    def test_correct_format_no_issues(self) -> None:
        fn = make_footnote(1, "Corporations Act 2001 (Cth) s 180.")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
            fields={"pinpoint_type_error": None, "has_comma_before_pinpoint": False},
        )
        assert validate_section_abbreviation(fn, pr) == []


class TestMediumNeutralPinpoint:
    def test_para_should_be_brackets(self) -> None:
        fn = make_footnote(1, "Palmer v Ayres [2017] HCA 5 at para 31.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True},
        )
        issue = validate_medium_neutral_pinpoint(fn, pr)
        assert issue is not None
        assert "[31]" in issue.suggested

    def test_correct_bracket_pinpoint(self) -> None:
        fn = make_footnote(1, "Palmer v Ayres [2017] HCA 5, [31].")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True},
        )
        assert validate_medium_neutral_pinpoint(fn, pr) is None


class TestDoubleSpacing:
    def test_detects_double_space(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland  (1992) 175 CLR 1.")
        issue = validate_double_spacing(fn)
        assert issue is not None

    def test_no_double_space(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1.")
        assert validate_double_spacing(fn) is None


class TestUppercaseV:
    """Test detection of uppercase 'V' in case names."""

    def test_uppercase_v_detected(self) -> None:
        fn = make_footnote(1, "Smith V Jones (1992) 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"has_v_error": True, "parties": "Smith V Jones"},
        )
        issue = validate_case_v_separator(fn, pr)
        assert issue is not None
        assert issue.suggested == "v"

    def test_lowercase_v_ok(self) -> None:
        fn = make_footnote(1, "Smith v Jones (1992) 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"has_v_error": False, "parties": "Smith v Jones"},
        )
        assert validate_case_v_separator(fn, pr) is None


class TestPinpointFormatArtifacts:
    """Test that pinpoint fixes don't create ' ,' or ', ,' artifacts."""

    def test_at_p_no_space_comma_artifact(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1 at p. 42.")
        pr = ParseResult(source_type=SourceType.CASE, confidence=0.9)
        issues = validate_pinpoint_format(fn, pr)
        at_issues = [i for i in issues if "at" in i.description or "p." in i.description]
        assert len(at_issues) >= 1
        # The current should include leading whitespace so replacement is clean
        assert at_issues[0].current.startswith(" ")
        assert at_issues[0].suggested == ", 42"

    def test_comma_pp_no_double_comma(self) -> None:
        fn = make_footnote(1, "HCA 16, pp. 5-25.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True},
        )
        issues = validate_pinpoint_format(fn, pr)
        pp_issues = [i for i in issues if "at" in i.description or "p." in i.description]
        assert len(pp_issues) >= 1
        # Should capture leading ", " so result is clean
        assert pp_issues[0].current.startswith(",")
        # Medium-neutral: should suggest bracket format
        assert "[5]" in pp_issues[0].suggested

    def test_at_page_captured_as_unit(self) -> None:
        fn = make_footnote(1, "NSWCA 299 at page 15.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True},
        )
        issues = validate_pinpoint_format(fn, pr)
        at_issues = [i for i in issues if "at" in i.description or "p." in i.description]
        assert len(at_issues) >= 1
        # "at page 15" should be captured as one unit including "at"
        assert "at" in at_issues[0].current
        assert at_issues[0].suggested == ", [15]"

    def test_books_skip_at_p_check(self) -> None:
        """Books should not get comma-prefixed pinpoint fixes."""
        fn = make_footnote(1, "Author, Title (Publisher, 2nd ed, 2020) p 45.")
        pr = ParseResult(source_type=SourceType.BOOK, confidence=0.9)
        issues = validate_pinpoint_format(fn, pr)
        # Should have no "at/p./page" issues for books (only en-dash if applicable)
        at_issues = [i for i in issues if "at" in i.description or "p." in i.description]
        assert len(at_issues) == 0


class TestMediumNeutralPinpointExtended:
    """Extended tests for medium-neutral pinpoint validation."""

    def test_at_paragraph_captured(self) -> None:
        fn = make_footnote(1, "Palmer v Ayres [2017] HCA 5 at paragraph 31.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True},
        )
        issue = validate_medium_neutral_pinpoint(fn, pr)
        assert issue is not None
        assert issue.suggested == ", [31]"

    def test_at_bracket_pinpoint(self) -> None:
        fn = make_footnote(1, "Smith v Jones [2023] WASC 456 at [31].")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True},
        )
        issue = validate_medium_neutral_pinpoint(fn, pr)
        assert issue is not None
        assert issue.suggested == ", [31]"

    def test_correct_bracket_pinpoint_with_comma(self) -> None:
        fn = make_footnote(1, "Smith v Jones [2023] WASC 456, [31].")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True},
        )
        assert validate_medium_neutral_pinpoint(fn, pr) is None

    def test_paragraph_range(self) -> None:
        fn = make_footnote(1, "Smith v Jones [2023] WASC 456 at para 5-10.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True},
        )
        issue = validate_medium_neutral_pinpoint(fn, pr)
        assert issue is not None
        assert "[5]" in issue.suggested
        assert "[10]" in issue.suggested


class TestPinpointComma:
    """Test detection of missing comma before case pinpoints."""

    def test_missing_comma_detected(self) -> None:
        fn = make_footnote(1, "ACCC v Baxter (2007) 232 ALJR 402 410.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"start_page": "402", "pinpoint": "410"},
        )
        issue = validate_pinpoint_comma(fn, pr)
        assert issue is not None
        assert issue.suggested == "402, 410"

    def test_comma_present_no_issue(self) -> None:
        fn = make_footnote(1, "ACCC v Baxter (2007) 232 ALJR 402, 410.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"start_page": "402", "pinpoint": "410"},
        )
        assert validate_pinpoint_comma(fn, pr) is None

    def test_non_case_skipped(self) -> None:
        fn = make_footnote(1, "Some legislation text.")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
            fields={"start_page": "402", "pinpoint": "410"},
        )
        assert validate_pinpoint_comma(fn, pr) is None


class TestCaseNameItalics:
    """Test case name italics validation."""

    def test_non_italic_case_detected(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"parties": "Mabo v Queensland", "italic_runs": []},
        )
        issue = validate_case_name_italics(fn, pr)
        assert issue is not None
        assert "italic" in issue.description.lower()

    def test_italic_case_no_issue(self) -> None:
        italic_run = FootnoteRun(text="Mabo v Queensland", italic=True)
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={
                "parties": "Mabo v Queensland",
                "italic_runs": [italic_run],
            },
        )
        assert validate_case_name_italics(fn, pr) is None


class TestIbidComma:
    """Test detection of erroneous comma before ibid pinpoint."""

    def test_comma_detected(self) -> None:
        fn = make_footnote(1, "Ibid, 55.")
        pr = ParseResult(
            source_type=SourceType.IBID,
            confidence=0.95,
            fields={
                "is_capitalised": True,
                "has_full_stop": True,
                "has_comma_before_pinpoint": True,
                "is_italic": True,
            },
        )
        issues = validate_ibid_format(fn, pr)
        comma_issues = [i for i in issues if "comma" in i.description.lower()]
        assert len(comma_issues) == 1
        assert comma_issues[0].rule == "1.4.1"
        assert comma_issues[0].auto_fixable is True

    def test_no_comma_no_issue(self) -> None:
        fn = make_footnote(1, "Ibid 55.")
        pr = ParseResult(
            source_type=SourceType.IBID,
            confidence=0.95,
            fields={
                "is_capitalised": True,
                "has_full_stop": True,
                "has_comma_before_pinpoint": False,
                "is_italic": True,
            },
        )
        issues = validate_ibid_format(fn, pr)
        comma_issues = [i for i in issues if "comma" in i.description.lower()]
        assert len(comma_issues) == 0


class TestIbidItalics:
    """Test detection of non-italic Ibid."""

    def test_non_italic_detected(self) -> None:
        fn = make_footnote(1, "Ibid.")
        pr = ParseResult(
            source_type=SourceType.IBID,
            confidence=0.95,
            fields={
                "is_capitalised": True,
                "has_full_stop": True,
                "has_comma_before_pinpoint": False,
                "is_italic": False,
            },
        )
        issues = validate_ibid_format(fn, pr)
        italic_issues = [i for i in issues if "italicised" in i.description.lower()]
        assert len(italic_issues) == 1
        assert italic_issues[0].rule == "1.4.1"
        assert italic_issues[0].severity == "warning"
        assert italic_issues[0].auto_fixable is True

    def test_italic_no_issue(self) -> None:
        fn = make_footnote(1, "Ibid.")
        pr = ParseResult(
            source_type=SourceType.IBID,
            confidence=0.95,
            fields={
                "is_capitalised": True,
                "has_full_stop": True,
                "has_comma_before_pinpoint": False,
                "is_italic": True,
            },
        )
        issues = validate_ibid_format(fn, pr)
        italic_issues = [i for i in issues if "italicised" in i.description.lower()]
        assert len(italic_issues) == 0


class TestSectionSpacing:
    """Test detection of missing space between section abbreviation and number."""

    def test_s180_detected(self) -> None:
        fn = make_footnote(1, "Corporations Act 2001 (Cth) s180.")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
        )
        issue = validate_section_spacing(fn, pr)
        assert issue is not None
        assert issue.rule == "3.2"
        assert issue.current == "s180"
        assert issue.suggested == "s 180"
        assert issue.auto_fixable is True

    def test_s_space_180_no_issue(self) -> None:
        fn = make_footnote(1, "Corporations Act 2001 (Cth) s 180.")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
        )
        issue = validate_section_spacing(fn, pr)
        assert issue is None


class TestInitialPeriods:
    """Test detection of periods in author initials (Rule 4.1.1)."""

    def test_hla_hart_detected(self) -> None:
        fn = make_footnote(1, "H.L.A. Hart, The Concept of Law (Clarendon Press, 1970) 15.")
        pr = ParseResult(
            source_type=SourceType.BOOK,
            confidence=0.9,
            fields={"has_initial_periods": True, "author": "H.L.A. Hart"},
        )
        issue = validate_initial_periods(fn, pr)
        assert issue is not None
        assert issue.rule == "4.1"
        assert issue.suggested == "HLA Hart"
        assert issue.auto_fixable is True

    def test_rj_ellicott_detected(self) -> None:
        fn = make_footnote(1, "R.J. Ellicott, 'Title' (2008) 82 Australian Law Journal 700.")
        pr = ParseResult(
            source_type=SourceType.JOURNAL_ARTICLE,
            confidence=0.9,
            fields={"has_initial_periods": True, "author": "R.J. Ellicott"},
        )
        issue = validate_initial_periods(fn, pr)
        assert issue is not None
        assert issue.suggested == "RJ Ellicott"

    def test_clean_initials_no_issue(self) -> None:
        fn = make_footnote(1, "HLA Hart, The Concept of Law (Clarendon Press, 1970) 15.")
        pr = ParseResult(
            source_type=SourceType.BOOK,
            confidence=0.9,
            fields={"has_initial_periods": False, "author": "HLA Hart"},
        )
        issue = validate_initial_periods(fn, pr)
        assert issue is None

    def test_non_secondary_skipped(self) -> None:
        fn = make_footnote(1, "H.L.A. v Something (1992) 175 CLR 1.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"has_initial_periods": True, "author": "H.L.A."},
        )
        issue = validate_initial_periods(fn, pr)
        assert issue is None


class TestJournalThePrefix:
    """Test detection of 'the' at start of journal name (Rule 5.5)."""

    def test_the_prefix_detected(self) -> None:
        fn = make_footnote(
            1,
            "Author, 'Title' (2020) 40 The Australian Law Journal 100.",
        )
        pr = ParseResult(
            source_type=SourceType.JOURNAL_ARTICLE,
            confidence=0.9,
            fields={
                "has_the_prefix": True,
                "journal_name": "The Australian Law Journal",
            },
        )
        issue = validate_journal_the_prefix(fn, pr)
        assert issue is not None
        assert issue.rule == "5.5"
        assert issue.suggested == "Australian Law Journal"
        assert issue.auto_fixable is True

    def test_no_the_no_issue(self) -> None:
        fn = make_footnote(
            1,
            "Author, 'Title' (2020) 40 Australian Law Journal 100.",
        )
        pr = ParseResult(
            source_type=SourceType.JOURNAL_ARTICLE,
            confidence=0.9,
            fields={
                "has_the_prefix": False,
                "journal_name": "Australian Law Journal",
            },
        )
        issue = validate_journal_the_prefix(fn, pr)
        assert issue is None

    def test_non_journal_skipped(self) -> None:
        fn = make_footnote(1, "Some book citation.")
        pr = ParseResult(
            source_type=SourceType.BOOK,
            confidence=0.9,
            fields={"has_the_prefix": True, "journal_name": "The Something"},
        )
        issue = validate_journal_the_prefix(fn, pr)
        assert issue is None


class TestBarePinpointBrackets:
    """Rule 1.1.6: Bare number pinpoints on medium-neutral citations need [brackets]."""

    def test_bare_number_flagged(self) -> None:
        """HCA 5, 31 → HCA 5, [31]"""
        fn = make_footnote(1, "Palmer v Ayres [2017] HCA 5, 31.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True, "pinpoint": "31"},
        )
        issue = validate_medium_neutral_pinpoint(fn, pr)
        assert issue is not None
        assert issue.rule == "1.1.6"
        assert issue.suggested == "[31]"
        assert issue.auto_fixable is True

    def test_bare_range_flagged(self) -> None:
        """HCA 16, 5-25 → HCA 16, [5]–[25]"""
        fn = make_footnote(1, "Roadshow Films v iiNet [2012] HCA 16, 5-25.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True, "pinpoint": "5-25"},
        )
        issue = validate_medium_neutral_pinpoint(fn, pr)
        assert issue is not None
        assert issue.suggested == "[5]–[25]"

    def test_bracketed_pinpoint_ok(self) -> None:
        """Already correct: [31]"""
        fn = make_footnote(1, "Palmer v Ayres [2017] HCA 5, [31].")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": True, "pinpoint": "[31]"},
        )
        issue = validate_medium_neutral_pinpoint(fn, pr)
        assert issue is None

    def test_not_medium_neutral_ignored(self) -> None:
        """Reported decisions: bare page pinpoints are correct."""
        fn = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1, 42.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"is_medium_neutral": False, "pinpoint": "42"},
        )
        issue = validate_medium_neutral_pinpoint(fn, pr)
        assert issue is None


class TestLegislationItalics:
    """Rule 3.1: Legislation title+year must be italicised, jurisdiction must NOT be."""

    def test_not_italic_flagged(self) -> None:
        fn = make_footnote(1, "Limitation Act 2005 (WA) s 14(1).")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
            fields={
                "title": "Limitation Act",
                "year": "2005",
                "title_is_italic": False,
                "jurisdiction_is_italic": False,
            },
        )
        issue = validate_legislation_italics(fn, pr)
        assert issue is not None
        assert issue.rule == "3.1"
        assert "italic" in issue.description.lower()
        assert issue.current == "Limitation Act 2005"

    def test_italic_ok(self) -> None:
        # "Limitation Act 2005" = chars 0..19
        fn = make_footnote(1, "Limitation Act 2005 (WA) s 14(1).", italic_ranges=[(0, 19)])
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
            fields={
                "title": "Limitation Act",
                "year": "2005",
                "title_is_italic": True,
                "jurisdiction_is_italic": False,
            },
        )
        issue = validate_legislation_italics(fn, pr)
        assert issue is None

    def test_jurisdiction_italic_flagged(self) -> None:
        fn = make_footnote(1, "Limitation Act 2005 (WA) s 14(1).")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.9,
            fields={
                "title": "Limitation Act",
                "year": "2005",
                "jurisdiction": "WA",
                "title_is_italic": True,
                "jurisdiction_is_italic": True,
            },
        )
        issue = validate_legislation_italics(fn, pr)
        assert issue is not None
        assert "not" in issue.description.lower()

    def test_non_legislation_ignored(self) -> None:
        fn = make_footnote(1, "Some case citation.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={"title_is_italic": False},
        )
        issue = validate_legislation_italics(fn, pr)
        assert issue is None


class TestJurisdictionFormat:
    """Rule 3.1: Jurisdiction must be abbreviated and in brackets."""

    def test_full_name_should_be_abbreviated(self) -> None:
        """(Western Australia) → (WA)"""
        fn = make_footnote(
            1, "Transfer of Land Act 1893 (Western Australia) sec. 68(1A)."
        )
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.95,
            fields={
                "jurisdiction": "WA",
                "jurisdiction_raw": "Western Australia",
                "jurisdiction_format": "bracketed",
                "jurisdiction_is_full_name": True,
            },
        )
        issues = validate_jurisdiction_format(fn, pr)
        assert len(issues) == 1
        assert issues[0].rule == "3.1"
        assert issues[0].current == "(Western Australia)"
        assert issues[0].suggested == "(WA)"
        assert issues[0].auto_fixable is True

    def test_bare_jurisdiction_needs_brackets(self) -> None:
        """NSW → (NSW)"""
        fn = make_footnote(
            1, "Legal Profession Uniform General Rules 2015 NSW regulation 42."
        )
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.90,
            fields={
                "jurisdiction": "NSW",
                "jurisdiction_raw": "NSW",
                "jurisdiction_format": "bare",
                "jurisdiction_is_full_name": False,
            },
        )
        issues = validate_jurisdiction_format(fn, pr)
        assert len(issues) == 1
        assert issues[0].current == "NSW"
        assert issues[0].suggested == "(NSW)"
        assert issues[0].auto_fixable is True

    def test_missing_jurisdiction_flagged(self) -> None:
        """No jurisdiction → warning"""
        fn = make_footnote(1, "Limitation Act 2005 §14(1).")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.85,
            fields={
                "title": "Limitation Act",
                "year": "2005",
                "jurisdiction": None,
                "jurisdiction_raw": None,
                "jurisdiction_format": "missing",
                "jurisdiction_is_full_name": False,
            },
        )
        issues = validate_jurisdiction_format(fn, pr)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].auto_fixable is False

    def test_correct_abbreviated_bracketed_no_issue(self) -> None:
        """Correct format: (Cth) — no issues"""
        fn = make_footnote(1, "Corporations Act 2001 (Cth) s 180(1).")
        pr = ParseResult(
            source_type=SourceType.LEGISLATION,
            confidence=0.95,
            fields={
                "jurisdiction": "Cth",
                "jurisdiction_raw": "Cth",
                "jurisdiction_format": "bracketed",
                "jurisdiction_is_full_name": False,
            },
        )
        issues = validate_jurisdiction_format(fn, pr)
        assert len(issues) == 0

    def test_non_legislation_ignored(self) -> None:
        fn = make_footnote(1, "Some case citation.")
        pr = ParseResult(
            source_type=SourceType.CASE,
            confidence=0.9,
            fields={},
        )
        issues = validate_jurisdiction_format(fn, pr)
        assert len(issues) == 0
