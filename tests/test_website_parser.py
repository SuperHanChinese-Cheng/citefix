"""Tests for the website citation parser."""

from __future__ import annotations

import pytest

from citefix.models import FootnoteRun, SourceType
from citefix.parsers.website import WebsiteParser


class TestWebsiteParserCanParse:
    def setup_method(self) -> None:
        self.parser = WebsiteParser()

    def test_full_website_high_confidence(self) -> None:
        text = (
            "Attorney-General's Department, 'Family Law' "
            "(Web Page, 15 March 2023) "
            "<https://www.ag.gov.au/families-and-marriage/families/family-law>."
        )
        assert self.parser.can_parse(text) >= 0.8

    def test_website_with_descriptor(self) -> None:
        text = (
            "High Court of Australia, 'Annual Report 2021-2022' "
            "(Report, 2022) "
            "<https://www.hcourt.gov.au/publications/annual-reports>."
        )
        assert self.parser.can_parse(text) >= 0.8

    def test_url_in_brackets_medium_confidence(self) -> None:
        text = "See <https://www.example.com/page>."
        conf = self.parser.can_parse(text)
        assert 0.5 <= conf < 0.8

    def test_bare_url_lower_confidence(self) -> None:
        text = "See https://www.example.com/page."
        conf = self.parser.can_parse(text)
        assert 0.3 <= conf < 0.7

    def test_case_citation_zero_confidence(self) -> None:
        assert self.parser.can_parse("Mabo v Queensland (1992) 175 CLR 1.") == 0.0

    def test_random_text_zero(self) -> None:
        assert self.parser.can_parse("Some random text without any URL.") == 0.0

    def test_url_brackets_with_quoted_title(self) -> None:
        text = "Someone, 'A Title' <https://www.example.com>."
        conf = self.parser.can_parse(text)
        assert conf >= 0.7


class TestWebsiteParserParse:
    def setup_method(self) -> None:
        self.parser = WebsiteParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        return self.parser.parse(text, runs).fields

    def test_ag_department_family_law(self) -> None:
        text = (
            "Attorney-General's Department, 'Family Law' "
            "(Web Page, 15 March 2023) "
            "<https://www.ag.gov.au/families-and-marriage/families/family-law>."
        )
        fields = self._parse(text)
        assert fields["author"] == "Attorney-General's Department"
        assert fields["title"] == "Family Law"
        assert fields["descriptor"] == "Web Page"
        assert fields["date"] == "15 March 2023"
        assert fields["url"] == "https://www.ag.gov.au/families-and-marriage/families/family-law"

    def test_high_court_annual_report(self) -> None:
        text = (
            "High Court of Australia, 'Annual Report 2021-2022' "
            "(Report, 2022) "
            "<https://www.hcourt.gov.au/publications/annual-reports>."
        )
        fields = self._parse(text)
        assert fields["author"] == "High Court of Australia"
        assert fields["title"] == "Annual Report 2021-2022"
        assert fields["descriptor"] == "Report"
        assert "2022" in fields["date"]
        assert fields["url"] == "https://www.hcourt.gov.au/publications/annual-reports"

    def test_website_name_field(self) -> None:
        text = (
            "John Smith, 'Understanding the Law', Legal Resources Online "
            "(Web Page, 1 January 2024) "
            "<https://www.legalresources.com/understanding>."
        )
        fields = self._parse(text)
        assert fields["author"] == "John Smith"
        assert fields["title"] == "Understanding the Law"
        assert fields["website_name"] == "Legal Resources Online"

    def test_no_descriptor(self) -> None:
        text = (
            "Department of Health, 'COVID-19 Guidelines' "
            "(10 April 2021) "
            "<https://www.health.gov.au/covid19>."
        )
        fields = self._parse(text)
        assert fields["author"] == "Department of Health"
        assert fields["title"] == "COVID-19 Guidelines"
        assert fields["descriptor"] is None
        assert fields["date"] == "10 April 2021"

    def test_url_in_angle_brackets(self) -> None:
        text = (
            "Attorney-General's Department, 'Family Law' "
            "(Web Page, 15 March 2023) "
            "<https://www.ag.gov.au/families-and-marriage/families/family-law>."
        )
        fields = self._parse(text)
        assert fields["url_in_angle_brackets"] is True

    def test_source_type_is_website(self) -> None:
        text = (
            "Attorney-General's Department, 'Family Law' "
            "(Web Page, 15 March 2023) "
            "<https://www.ag.gov.au/families-and-marriage/families/family-law>."
        )
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.source_type == SourceType.WEBSITE
        assert result.confidence >= 0.8

    def test_partial_parse_bare_url(self) -> None:
        text = "See some reference at https://www.example.com/page."
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.source_type == SourceType.WEBSITE
        assert result.fields["url"] == "https://www.example.com/page."
        assert "parse_error" in result.fields

    def test_partial_parse_url_in_brackets(self) -> None:
        text = "Some incomplete citation <https://www.example.com/page>."
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.source_type == SourceType.WEBSITE
        assert result.fields["url"] == "https://www.example.com/page"
        assert result.fields["url_in_angle_brackets"] is True

    def test_unparseable_returns_unknown(self) -> None:
        runs = [FootnoteRun(text="Just some random text.")]
        result = self.parser.parse("Just some random text.", runs)
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0

    def test_year_only_date(self) -> None:
        """Some website citations use year-only dates like (Report, 2022)."""
        text = (
            "High Court of Australia, 'Annual Report 2021-2022' "
            "(Report, 2022) "
            "<https://www.hcourt.gov.au/publications/annual-reports>."
        )
        fields = self._parse(text)
        assert "2022" in fields["date"]
