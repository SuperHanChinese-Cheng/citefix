"""Tests for the report citation parser."""

from __future__ import annotations

import pytest

from citefix.models import FootnoteRun, SourceType
from citefix.parsers.report import ReportParser


class TestReportParserCanParse:
    def setup_method(self) -> None:
        self.parser = ReportParser()

    def test_alrc_report_high_confidence(self) -> None:
        text = (
            "Australian Law Reform Commission, Traditional Rights and Freedoms: "
            "Encroachments by Commonwealth Laws (Report No 129, 2015)."
        )
        assert self.parser.can_parse(text) >= 0.8

    def test_royal_commission_no_body(self) -> None:
        text = (
            "Royal Commission into Misconduct in the Banking, Superannuation "
            "and Financial Services Industry (Final Report, 2019)."
        )
        assert self.parser.can_parse(text) >= 0.6

    def test_productivity_commission_high_confidence(self) -> None:
        text = (
            "Productivity Commission, Access to Justice Arrangements "
            "(Inquiry Report No 72, 2014) 102."
        )
        assert self.parser.can_parse(text) >= 0.8

    def test_case_citation_zero_confidence(self) -> None:
        assert self.parser.can_parse("Mabo v Queensland (1992) 175 CLR 1.") == 0.0

    def test_random_text_zero(self) -> None:
        assert self.parser.can_parse("Some random sentence about nothing.") == 0.0

    def test_discussion_paper(self) -> None:
        text = (
            "Australian Law Reform Commission, Serious Invasions of Privacy "
            "in the Digital Era (Discussion Paper, 2014)."
        )
        assert self.parser.can_parse(text) >= 0.8

    def test_legislation_zero_confidence(self) -> None:
        assert self.parser.can_parse("Corporations Act 2001 (Cth) s 180(1).") == 0.0


class TestReportParserParse:
    def setup_method(self) -> None:
        self.parser = ReportParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        return self.parser.parse(text, runs).fields

    def test_alrc_report(self) -> None:
        text = (
            "Australian Law Reform Commission, Traditional Rights and Freedoms: "
            "Encroachments by Commonwealth Laws (Report No 129, 2015)."
        )
        fields = self._parse(text)
        assert fields["body"] == "Australian Law Reform Commission"
        assert fields["title"] == "Traditional Rights and Freedoms: Encroachments by Commonwealth Laws"
        assert fields["report_number"] == "129"
        assert fields["year"] == "2015"
        assert fields["pinpoint"] is None

    def test_productivity_commission_with_pinpoint(self) -> None:
        text = (
            "Productivity Commission, Access to Justice Arrangements "
            "(Inquiry Report No 72, 2014) 102."
        )
        fields = self._parse(text)
        assert fields["body"] == "Productivity Commission"
        assert fields["title"] == "Access to Justice Arrangements"
        assert fields["report_number"] == "72"
        assert fields["year"] == "2014"
        assert fields["pinpoint"] == "102"

    def test_royal_commission_title_only(self) -> None:
        text = (
            "Royal Commission into Misconduct in the Banking, Superannuation "
            "and Financial Services Industry (Final Report, 2019)."
        )
        fields = self._parse(text)
        # The entire text before the parenthetical is the title; no separate body
        assert fields["body"] is None
        assert "Royal Commission" in fields["title"]
        assert fields["year"] == "2019"

    def test_report_no_number(self) -> None:
        text = (
            "Australian Law Reform Commission, Family Violence: "
            "A National Legal Response (Final Report, 2010)."
        )
        fields = self._parse(text)
        assert fields["body"] == "Australian Law Reform Commission"
        assert fields["report_number"] is None
        assert fields["year"] == "2010"
        assert "report_descriptor" in fields

    def test_source_type_is_report(self) -> None:
        text = (
            "Australian Law Reform Commission, Traditional Rights and Freedoms: "
            "Encroachments by Commonwealth Laws (Report No 129, 2015)."
        )
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.source_type == SourceType.REPORT
        assert result.confidence >= 0.8

    def test_title_italic_detection(self) -> None:
        title = "Access to Justice Arrangements"
        text = f"Productivity Commission, {title} (Inquiry Report No 72, 2014)."
        runs = [
            FootnoteRun(text="Productivity Commission, "),
            FootnoteRun(text=title, italic=True),
            FootnoteRun(text=" (Inquiry Report No 72, 2014)."),
        ]
        result = self.parser.parse(text, runs)
        assert result.fields["title_is_italic"] is True

    def test_title_not_italic_detection(self) -> None:
        text = (
            "Productivity Commission, Access to Justice Arrangements "
            "(Inquiry Report No 72, 2014)."
        )
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.fields["title_is_italic"] is False

    def test_discussion_paper_fields(self) -> None:
        text = (
            "Australian Law Reform Commission, Serious Invasions of Privacy "
            "in the Digital Era (Discussion Paper, 2014)."
        )
        fields = self._parse(text)
        assert "Discussion Paper" in fields["report_descriptor"]
        assert fields["year"] == "2014"

    def test_unparseable_returns_unknown(self) -> None:
        runs = [FootnoteRun(text="Just some random text.")]
        result = self.parser.parse("Just some random text.", runs)
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0
