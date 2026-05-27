"""Tests for the legislation citation parser."""

from __future__ import annotations

import pytest

from citefix.models import FootnoteRun, SourceType
from citefix.parsers.legislation import LegislationParser
from citefix.signals import strip_introductory_signal


class TestLegislationParserCanParse:
    def setup_method(self) -> None:
        self.parser = LegislationParser()

    def test_full_legislation_high_confidence(self) -> None:
        assert self.parser.can_parse("Corporations Act 2001 (Cth) s 180(1).") >= 0.9

    def test_legislation_without_pinpoint(self) -> None:
        assert self.parser.can_parse("Fair Work Act 2009 (Cth).") >= 0.9

    def test_case_citation_low_confidence(self) -> None:
        assert self.parser.can_parse("Mabo v Queensland (1992) 175 CLR 1.") < 0.5

    def test_random_text_zero(self) -> None:
        assert self.parser.can_parse("Some random text.") == 0.0

    def test_act_without_jurisdiction(self) -> None:
        conf = self.parser.can_parse("Corporations Act 2001 s 180.")
        assert 0.8 <= conf <= 0.9  # No-jurisdiction pattern matches at 0.85


class TestLegislationParserParse:
    def setup_method(self) -> None:
        self.parser = LegislationParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        return result.fields

    def test_corporations_act(self) -> None:
        fields = self._parse("Corporations Act 2001 (Cth) s 180(1).")
        assert fields["title"] == "Corporations Act"
        assert fields["year"] == "2001"
        assert fields["jurisdiction"] == "Cth"
        assert fields["pinpoint_type"] == "s"
        assert fields["pinpoint"] == "180(1)"

    def test_limitation_act_wa(self) -> None:
        fields = self._parse("Limitation Act 2005 (WA) s 14(1).")
        assert fields["title"] == "Limitation Act"
        assert fields["year"] == "2005"
        assert fields["jurisdiction"] == "WA"
        assert fields["pinpoint"] == "14(1)"

    def test_fair_work_act_no_pinpoint(self) -> None:
        fields = self._parse("Fair Work Act 2009 (Cth).")
        assert fields["title"] == "Fair Work Act"
        assert fields["year"] == "2009"
        assert fields["jurisdiction"] == "Cth"
        assert fields["pinpoint"] is None

    def test_detects_comma_before_section(self) -> None:
        """Common error: 'Act 2001 (Cth), s 180' — comma before section."""
        fields = self._parse("Corporations Act 2001 (Cth), s 180(1).")
        assert fields["has_comma_before_pinpoint"] is True

    def test_no_comma_when_correct(self) -> None:
        fields = self._parse("Corporations Act 2001 (Cth) s 180(1).")
        assert fields["has_comma_before_pinpoint"] is False

    def test_detects_section_spelled_out(self) -> None:
        """'Section' should be abbreviated to 's'."""
        fields = self._parse("Corporations Act 2001 (Cth) Section 180(1).")
        assert fields["pinpoint_type_error"] == "Section"

    def test_detects_section_symbol(self) -> None:
        """'§' should be 's'."""
        fields = self._parse("Corporations Act 2001 (Cth) § 180(1).")
        assert fields["pinpoint_type_error"] == "§"

    def test_correct_s_no_error(self) -> None:
        fields = self._parse("Corporations Act 2001 (Cth) s 180(1).")
        assert fields["pinpoint_type_error"] is None

    def test_regulation(self) -> None:
        fields = self._parse("Family Law Rules 2004 (Cth) r 13.04.")
        assert fields["title"] == "Family Law Rules"
        assert fields["pinpoint_type"] == "r"
        assert fields["pinpoint"] == "13.04"

    def test_nsw_jurisdiction(self) -> None:
        fields = self._parse("Crimes Act 1900 (NSW) s 61.")
        assert fields["jurisdiction"] == "NSW"

    def test_vic_jurisdiction(self) -> None:
        fields = self._parse("Charter of Human Rights and Responsibilities Act 2006 (Vic) s 7.")
        assert fields["jurisdiction"] == "Vic"

    def test_schedule_pinpoint(self) -> None:
        fields = self._parse("Corporations Act 2001 (Cth) sch 2.")
        assert fields["pinpoint_type"] == "sch"
        assert fields["pinpoint"] == "2"

    def test_multiple_sections(self) -> None:
        fields = self._parse("Fair Work Act 2009 (Cth) ss 394, 396.")
        assert fields["pinpoint_type"] == "ss"

    def test_transfer_of_land_act(self) -> None:
        fields = self._parse("Transfer of Land Act 1893 (WA) s 68(1A).")
        assert fields["title"] == "Transfer of Land Act"
        assert fields["pinpoint"] == "68(1A)"


class TestLegislationParserWithSignals:
    """Test that introductory signals are stripped before parsing."""

    def setup_method(self) -> None:
        self.parser = LegislationParser()

    def _parse_with_signal(self, text: str) -> dict:
        _signal, stripped = strip_introductory_signal(text)
        runs = [FootnoteRun(text=stripped)]
        return self.parser.parse(stripped, runs).fields

    def test_see_not_in_title(self) -> None:
        """'See' should be stripped, not included in legislation title."""
        fields = self._parse_with_signal("See Corporations Act 2001 (Cth) s 180(1).")
        assert fields["title"] == "Corporations Act"
        assert "See" not in fields["title"]
        assert fields["jurisdiction"] == "Cth"

    def test_see_also_not_in_title(self) -> None:
        fields = self._parse_with_signal("See also Fair Work Act 2009 (Cth) s 394.")
        assert fields["title"] == "Fair Work Act"
        assert "See" not in fields["title"]

    def test_cf_not_in_title(self) -> None:
        fields = self._parse_with_signal("Cf Limitation Act 2005 (WA) s 14(1).")
        assert fields["title"] == "Limitation Act"
        assert "Cf" not in fields["title"]


class TestLegislationParserFullNameJurisdiction:
    """Test parsing legislation with full jurisdiction names like (Western Australia)."""

    def setup_method(self) -> None:
        self.parser = LegislationParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        return result.fields

    def test_western_australia_full_name(self) -> None:
        fields = self._parse("Transfer of Land Act 1893 (Western Australia) sec. 68(1A).")
        assert fields["title"] == "Transfer of Land Act"
        assert fields["year"] == "1893"
        assert fields["jurisdiction"] == "WA"
        assert fields["jurisdiction_raw"] == "Western Australia"
        assert fields["jurisdiction_is_full_name"] is True
        assert fields["jurisdiction_format"] == "bracketed"

    def test_commonwealth_full_name(self) -> None:
        fields = self._parse("Corporations Act 2001 (Commonwealth) s 180(1).")
        assert fields["jurisdiction"] == "Cth"
        assert fields["jurisdiction_raw"] == "Commonwealth"
        assert fields["jurisdiction_is_full_name"] is True

    def test_new_south_wales_full_name(self) -> None:
        fields = self._parse("Crimes Act 1900 (New South Wales) s 61.")
        assert fields["jurisdiction"] == "NSW"
        assert fields["jurisdiction_is_full_name"] is True

    def test_can_parse_confidence(self) -> None:
        conf = self.parser.can_parse(
            "Transfer of Land Act 1893 (Western Australia) sec. 68(1A)."
        )
        assert conf >= 0.9


class TestLegislationParserBareJurisdiction:
    """Test parsing legislation with bare jurisdiction (no brackets)."""

    def setup_method(self) -> None:
        self.parser = LegislationParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        return result.fields

    def test_bare_nsw(self) -> None:
        fields = self._parse("Legal Profession Uniform General Rules 2015 NSW regulation 42.")
        assert fields["title"] == "Legal Profession Uniform General Rules"
        assert fields["year"] == "2015"
        assert fields["jurisdiction"] == "NSW"
        assert fields["jurisdiction_format"] == "bare"
        assert fields["pinpoint_type"] == "regulation"
        assert fields["pinpoint"] == "42"

    def test_bare_cth(self) -> None:
        fields = self._parse("Fair Work Act 2009 Cth s 394.")
        assert fields["jurisdiction"] == "Cth"
        assert fields["jurisdiction_format"] == "bare"

    def test_can_parse_confidence(self) -> None:
        conf = self.parser.can_parse(
            "Legal Profession Uniform General Rules 2015 NSW regulation 42."
        )
        assert conf >= 0.85


class TestLegislationParserNoJurisdiction:
    """Test parsing legislation with no jurisdiction at all."""

    def setup_method(self) -> None:
        self.parser = LegislationParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        return result.fields

    def test_section_symbol_no_space(self) -> None:
        fields = self._parse("Limitation Act 2005 §14(1).")
        assert fields["title"] == "Limitation Act"
        assert fields["year"] == "2005"
        assert fields["jurisdiction"] is None
        assert fields["jurisdiction_format"] == "missing"
        assert fields["pinpoint_type"] == "§"
        assert fields["pinpoint"] == "14(1)"
        assert fields["has_pinpoint_spacing_error"] is True

    def test_section_with_space(self) -> None:
        fields = self._parse("Corporations Act 2001 s 180.")
        assert fields["title"] == "Corporations Act"
        assert fields["jurisdiction"] is None
        assert fields["jurisdiction_format"] == "missing"
        assert fields["pinpoint"] == "180"

    def test_can_parse_confidence(self) -> None:
        conf = self.parser.can_parse("Limitation Act 2005 §14(1).")
        assert conf >= 0.8


class TestLegislationItalicDetection:
    """Test that the parser correctly detects italic / non-italic title."""

    def setup_method(self) -> None:
        self.parser = LegislationParser()

    def test_non_italic_detected(self) -> None:
        """Plain text — title_is_italic should be False."""
        text = "Limitation Act 2005 (WA) s 14(1)."
        runs = [FootnoteRun(text=text, italic=False)]
        result = self.parser.parse(text, runs)
        assert result.fields["title_is_italic"] is False

    def test_italic_detected(self) -> None:
        """Title in italic run — title_is_italic should be True."""
        text = "Limitation Act 2005 (WA) s 14(1)."
        runs = [
            FootnoteRun(text="Limitation Act 2005", italic=True),
            FootnoteRun(text=" (WA) s 14(1).", italic=False),
        ]
        result = self.parser.parse(text, runs)
        assert result.fields["title_is_italic"] is True

    def test_all_in_one_non_italic_run(self) -> None:
        """Everything in one non-italic run — should NOT be detected as italic.

        This tests the operator precedence bug fix: the old code evaluated as
        (r.italic AND title_year in r.text) OR (title in r.text)
        which always returned True when title appeared in any run.
        """
        text = "Corporations Act 2001 (Cth) s 180(1)."
        runs = [FootnoteRun(text=text, italic=False)]
        result = self.parser.parse(text, runs)
        assert result.fields["title_is_italic"] is False
