"""Tests for the case citation parser."""

from __future__ import annotations

import pytest

from citefix.models import FootnoteRun, SourceType
from citefix.parsers.case import CaseCitationParser
from citefix.signals import strip_introductory_signal


class TestCaseParserCanParse:
    def setup_method(self) -> None:
        self.parser = CaseCitationParser()

    def test_reported_case_high_confidence(self) -> None:
        assert self.parser.can_parse("Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.") >= 0.9

    def test_medium_neutral_high_confidence(self) -> None:
        assert self.parser.can_parse("Palmer v Ayres [2017] HCA 5, [31].") >= 0.8

    def test_no_v_separator_zero_confidence(self) -> None:
        assert self.parser.can_parse("Corporations Act 2001 (Cth) s 180(1).") < 0.3

    def test_vs_still_detectable(self) -> None:
        assert self.parser.can_parse("Mabo vs Queensland (1992) 175 CLR 1.") >= 0.5

    def test_random_text_zero(self) -> None:
        assert self.parser.can_parse("Some random sentence.") == 0.0


class TestCaseParserParse:
    def setup_method(self) -> None:
        self.parser = CaseCitationParser()

    def _parse(self, text: str, italic_text: str | None = None) -> dict:
        runs = [FootnoteRun(text=text)]
        if italic_text:
            runs = [
                FootnoteRun(text=italic_text, italic=True),
                FootnoteRun(text=text[len(italic_text):]),
            ]
        result = self.parser.parse(text, runs)
        return result.fields

    def test_mabo_full_citation(self) -> None:
        fields = self._parse("Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.")
        assert fields["parties"] == "Mabo v Queensland (No 2)"
        assert fields["year"] == "1992"
        assert fields["year_bracket_open"] == "("
        assert fields["volume"] == "175"
        assert fields["report_series"] == "CLR"
        assert fields["start_page"] == "1"
        assert fields["pinpoint"] == "42"
        assert fields["is_medium_neutral"] is False

    def test_palmer_medium_neutral(self) -> None:
        fields = self._parse("Palmer v Ayres [2017] HCA 5, [31].")
        assert fields["parties"] == "Palmer v Ayres"
        assert fields["year"] == "2017"
        assert fields["report_series"] == "HCA"
        assert fields["start_page"] == "5"
        assert fields["pinpoint"] == "[31]"
        assert fields["is_medium_neutral"] is True

    def test_detects_vs_error(self) -> None:
        fields = self._parse("Mabo vs Queensland (No 2) (1992) 175 CLR 1.")
        assert fields["has_v_error"] is True

    def test_detects_versus_error(self) -> None:
        fields = self._parse("Mabo versus Queensland (No 2) (1992) 175 CLR 1.")
        assert fields["has_v_error"] is True

    def test_correct_v_no_error(self) -> None:
        fields = self._parse("Mabo v Queensland (No 2) (1992) 175 CLR 1.")
        assert fields["has_v_error"] is False

    def test_wrong_bracket_type_detected(self) -> None:
        """CLR uses round brackets — square brackets here should be parsed as-is for validation."""
        fields = self._parse("Mabo v Queensland (No 2) [1992] 175 CLR 1.")
        assert fields["year_bracket_open"] == "["
        assert fields["report_series"] == "CLR"

    def test_case_with_at_p_pinpoint(self) -> None:
        fields = self._parse("Mabo v Queensland (No 2) (1992) 175 CLR 1 at p. 42.")
        assert fields["pinpoint"] == "42"

    def test_nswsc_medium_neutral(self) -> None:
        fields = self._parse("Smith v Jones [2023] NSWSC 456.")
        assert fields["report_series"] == "NSWSC"
        assert fields["is_medium_neutral"] is True
        assert fields["year_bracket_open"] == "["

    def test_case_no_pinpoint(self) -> None:
        fields = self._parse("Mabo v Queensland (No 2) (1992) 175 CLR 1.")
        assert fields["pinpoint"] is None

    def test_roadshow_films(self) -> None:
        fields = self._parse("Roadshow Films Pty Ltd v iiNet Ltd [2012] HCA 16, [5].")
        assert "Roadshow Films Pty Ltd" in fields["parties"]
        assert fields["year"] == "2012"
        assert fields["report_series"] == "HCA"

    def test_page_range_with_hyphen(self) -> None:
        fields = self._parse("Palmer v Ayres (2017) 259 CLR 478, 487-490.")
        assert fields["pinpoint"] == "487-490"

    def test_nswlr_round_brackets(self) -> None:
        fields = self._parse("Smith v Jones (2020) 100 NSWLR 55.")
        assert fields["year_bracket_open"] == "("
        assert fields["report_series"] == "NSWLR"

    def test_fcafc_square_brackets(self) -> None:
        fields = self._parse("Smith v Jones [2021] FCAFC 100, [45].")
        assert fields["year_bracket_open"] == "["
        assert fields["report_series"] == "FCAFC"

    def test_uppercase_v_detected(self) -> None:
        """Uppercase 'V' should be parsed and flagged as error."""
        fields = self._parse("Roadshow Films Pty Ltd V iiNet Ltd [2012] HCA 16.")
        assert fields["has_v_error"] is True
        assert "V" in fields["parties"] or "v" in fields["parties"]

    def test_medium_neutral_with_round_brackets(self) -> None:
        """Medium-neutral citations with wrong bracket type should still parse."""
        fields = self._parse("Palmer versus Ayres (2017) HCA 5 at paragraph 31.")
        assert fields["year"] == "2017"
        assert fields["report_series"] == "HCA"
        assert fields["is_medium_neutral"] is True
        assert fields["has_v_error"] is True

    def test_pp_range_medium_neutral(self) -> None:
        """pp. prefix with range should be parsed for medium-neutral citations."""
        fields = self._parse("Roadshow Films Pty Ltd v iiNet Ltd [2012] HCA 16, pp. 5-25.")
        assert fields["pinpoint"] == "5-25"
        assert fields["is_medium_neutral"] is True

    def test_qd_r_with_space_square_brackets(self) -> None:
        """Qd R (Queensland Reports) uses square brackets — AGLC4 r 2.2.1."""
        fields = self._parse("King v King [1974] Qd R 253.")
        assert fields["report_series"] == "Qd R"
        assert fields["year_bracket_open"] == "["
        assert fields["year"] == "1974"
        assert fields["start_page"] == "253"
        assert fields["is_medium_neutral"] is False

    def test_qd_r_volume_square_brackets(self) -> None:
        """Qd R with volume number still uses square brackets."""
        fields = self._parse("Total Ice Pty Ltd v Maroochy Shire Council [2009] 1 Qd R 82, 89.")
        assert fields["report_series"] == "Qd R"
        assert fields["year_bracket_open"] == "["
        assert fields["volume"] == "1"
        assert fields["start_page"] == "82"
        assert fields["pinpoint"] == "89"

    def test_ntr_round_brackets(self) -> None:
        """NTR (Northern Territory Reports) uses round brackets."""
        fields = self._parse("Smith v Jones (1985) 20 NTR 100.")
        assert fields["report_series"] == "NTR"
        assert fields["year_bracket_open"] == "("
        assert fields["is_medium_neutral"] is False


class TestCaseParserWithSignals:
    """Test that introductory signals are stripped before parsing."""

    def setup_method(self) -> None:
        self.parser = CaseCitationParser()

    def _parse_with_signal(self, text: str) -> dict:
        _signal, stripped = strip_introductory_signal(text)
        runs = [FootnoteRun(text=stripped)]
        return self.parser.parse(stripped, runs).fields

    def test_see_not_in_parties(self) -> None:
        """'See' should be stripped, not included in parties."""
        fields = self._parse_with_signal(
            "See Mabo v Queensland (No 2) (1992) 175 CLR 1, 42."
        )
        assert fields["parties"] == "Mabo v Queensland (No 2)"
        assert "See" not in fields["parties"]
        assert fields["year"] == "1992"
        assert fields["report_series"] == "CLR"
        assert fields["pinpoint"] == "42"

    def test_see_also_not_in_parties(self) -> None:
        """'See also' should be stripped, not included in parties."""
        fields = self._parse_with_signal(
            "See also Palmer v Ayres [2017] HCA 5, [31]."
        )
        assert fields["parties"] == "Palmer v Ayres"
        assert "See" not in fields["parties"]
        assert fields["report_series"] == "HCA"

    def test_cf_not_in_parties(self) -> None:
        """'Cf' should be stripped, not included in parties."""
        fields = self._parse_with_signal(
            "Cf Roadshow Films Pty Ltd v iiNet Ltd [2012] HCA 16."
        )
        assert "Roadshow Films Pty Ltd" in fields["parties"]
        assert "Cf" not in fields["parties"]

    def test_but_see_not_in_parties(self) -> None:
        """'But see' should be stripped, not included in parties."""
        fields = self._parse_with_signal(
            "But see Smith v Jones (2020) 100 NSWLR 55."
        )
        assert fields["parties"] == "Smith v Jones"
        assert "But" not in fields["parties"]

    def test_no_signal_unchanged(self) -> None:
        """Citation without signal should parse identically."""
        fields = self._parse_with_signal(
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42."
        )
        assert fields["parties"] == "Mabo v Queensland (No 2)"
        assert fields["year"] == "1992"

    def test_can_parse_with_signal_stripped(self) -> None:
        """can_parse should return high confidence on signal-stripped text."""
        _signal, stripped = strip_introductory_signal(
            "See Mabo v Queensland (No 2) (1992) 175 CLR 1."
        )
        assert self.parser.can_parse(stripped) >= 0.9


class TestNonAdversarialCases:
    """Tests for non-adversarial case formats (Re, Ex parte, In re, In the matter of)."""

    def setup_method(self) -> None:
        self.parser = CaseCitationParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        return result.fields

    def test_re_case_reported_can_parse(self) -> None:
        """Re format case with reported citation should be parseable."""
        text = (
            "Re Minister for Immigration and Multicultural Affairs;"
            " Ex Parte Applicant S20/2002 (2003) 198 ALR 59, 65."
        )
        assert self.parser.can_parse(text) >= 0.85

    def test_re_case_reported_fields(self) -> None:
        """Re format case with reported citation — verify extracted fields."""
        text = (
            "Re Minister for Immigration and Multicultural Affairs;"
            " Ex Parte Applicant S20/2002 (2003) 198 ALR 59, 65."
        )
        result = self.parser.parse(text, [FootnoteRun(text=text)])
        assert result.source_type == SourceType.CASE
        assert "Re Minister" in result.fields["parties"]
        assert result.fields["year"] == "2003"
        assert result.fields["report_series"] == "ALR"
        assert result.fields["volume"] == "198"
        assert result.fields["start_page"] == "59"
        assert result.fields["pinpoint"] == "65"
        assert result.fields["has_v_error"] is False
        assert result.fields["has_v_period"] is False

    def test_ex_parte_case(self) -> None:
        """Ex parte case format."""
        text = "Ex parte Walsh (1942) 66 CLR 545."
        assert self.parser.can_parse(text) >= 0.85
        result = self.parser.parse(text, [FootnoteRun(text=text)])
        assert result.source_type == SourceType.CASE
        assert "Ex parte Walsh" in result.fields["parties"]
        assert result.fields["year"] == "1942"
        assert result.fields["report_series"] == "CLR"
        assert result.fields["volume"] == "66"
        assert result.fields["start_page"] == "545"

    def test_re_case_medium_neutral(self) -> None:
        """Re format with medium-neutral citation."""
        text = "Re Application under the Major Crime (Investigative Powers) Act 2004 [2009] VSC 381."
        assert self.parser.can_parse(text) >= 0.85
        result = self.parser.parse(text, [FootnoteRun(text=text)])
        assert result.source_type == SourceType.CASE
        assert "Re Application" in result.fields["parties"]
        assert result.fields["year"] == "2009"
        assert result.fields["report_series"] == "VSC"
        assert result.fields["start_page"] == "381"
        assert result.fields["is_medium_neutral"] is True

    def test_in_re_format(self) -> None:
        """In re format case."""
        text = "In re Company X (2010) 240 CLR 100."
        assert self.parser.can_parse(text) >= 0.85
        result = self.parser.parse(text, [FootnoteRun(text=text)])
        assert result.source_type == SourceType.CASE
        assert "In re Company X" in result.fields["parties"]
        assert result.fields["year"] == "2010"
        assert result.fields["report_series"] == "CLR"

    def test_in_the_matter_of_format(self) -> None:
        """In the matter of format case."""
        text = "In the matter of Smith (2015) 300 ALR 200, 210."
        assert self.parser.can_parse(text) >= 0.85
        result = self.parser.parse(text, [FootnoteRun(text=text)])
        assert result.source_type == SourceType.CASE
        assert "In the matter of Smith" in result.fields["parties"]
        assert result.fields["year"] == "2015"
        assert result.fields["report_series"] == "ALR"
        assert result.fields["pinpoint"] == "210"

    def test_re_case_no_pinpoint(self) -> None:
        """Re case without a pinpoint reference."""
        fields = self._parse("Ex parte Walsh (1942) 66 CLR 545.")
        assert fields["pinpoint"] is None

    def test_re_case_not_medium_neutral_for_clr(self) -> None:
        """Re case with CLR should not be flagged as medium neutral."""
        fields = self._parse("Re Wakim (1999) 198 CLR 511.")
        assert fields["is_medium_neutral"] is False
        assert fields["report_series"] == "CLR"

    def test_re_case_medium_neutral_hca(self) -> None:
        """Re case with HCA court identifier."""
        text = "Re Patterson [2001] HCA 51."
        result = self.parser.parse(text, [FootnoteRun(text=text)])
        assert result.source_type == SourceType.CASE
        assert result.fields["is_medium_neutral"] is True
        assert result.fields["year"] == "2001"
        assert result.fields["report_series"] == "HCA"

    def test_re_case_with_no_period(self) -> None:
        """Re case with (No.) should detect the period error."""
        text = "Re Application (No. 2) (2010) 240 CLR 100."
        fields = self._parse(text)
        assert fields["has_no_period"] is True

    def test_re_case_round_brackets_year(self) -> None:
        """Re case with round brackets for year (reported series)."""
        fields = self._parse("Re Wakim (1999) 198 CLR 511.")
        assert fields["year_bracket_open"] == "("
        assert fields["year_bracket_close"] == ")"

    def test_re_case_square_brackets_year(self) -> None:
        """Re case with square brackets for year (medium neutral)."""
        fields = self._parse("Re Patterson [2001] HCA 51.")
        assert fields["year_bracket_open"] == "["
        assert fields["year_bracket_close"] == "]"

    def test_ex_parte_lowercase_p(self) -> None:
        """Ex parte with lowercase 'p' in 'parte'."""
        text = "Ex parte Jones (2005) 220 CLR 1."
        assert self.parser.can_parse(text) >= 0.85
        result = self.parser.parse(text, [FootnoteRun(text=text)])
        assert result.source_type == SourceType.CASE
        assert "Ex parte Jones" in result.fields["parties"]

    def test_random_text_still_zero(self) -> None:
        """Non-case text should still return zero confidence."""
        assert self.parser.can_parse("Some random sentence about Re:starting things.") == 0.0
