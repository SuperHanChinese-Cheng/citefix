"""Tests for the treaty citation parser."""

from __future__ import annotations

import pytest

from citefix.models import FootnoteRun, SourceType
from citefix.parsers.treaty import TreatyParser


class TestTreatyParserCanParse:
    def setup_method(self) -> None:
        self.parser = TreatyParser()

    def test_iccpr_high_confidence(self) -> None:
        text = (
            "International Covenant on Civil and Political Rights, "
            "opened for signature 16 December 1966, "
            "999 UNTS 171 (entered into force 23 March 1976)."
        )
        assert self.parser.can_parse(text) >= 0.8

    def test_crc_high_confidence(self) -> None:
        text = (
            "Convention on the Rights of the Child, "
            "opened for signature 20 November 1989, "
            "1577 UNTS 3 (entered into force 2 September 1990)."
        )
        assert self.parser.can_parse(text) >= 0.8

    def test_case_citation_zero_confidence(self) -> None:
        assert self.parser.can_parse("Mabo v Queensland (1992) 175 CLR 1.") == 0.0

    def test_random_text_zero(self) -> None:
        assert self.parser.can_parse("Some random sentence about nothing.") == 0.0

    def test_partial_treaty_medium_confidence(self) -> None:
        """Treaty with 'opened for signature' but missing other parts."""
        text = "Convention on Biodiversity, opened for signature 5 June 1992."
        conf = self.parser.can_parse(text)
        assert 0.3 <= conf < 0.8

    def test_treaty_keyword_with_series(self) -> None:
        """Has treaty keyword and series reference but not full pattern."""
        text = "Some Convention 999 UNTS 171."
        conf = self.parser.can_parse(text)
        assert conf >= 0.5

    def test_legislation_zero_confidence(self) -> None:
        assert self.parser.can_parse("Corporations Act 2001 (Cth) s 180(1).") == 0.0


class TestTreatyParserParse:
    def setup_method(self) -> None:
        self.parser = TreatyParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        return self.parser.parse(text, runs).fields

    def test_iccpr(self) -> None:
        text = (
            "International Covenant on Civil and Political Rights, "
            "opened for signature 16 December 1966, "
            "999 UNTS 171 (entered into force 23 March 1976)."
        )
        fields = self._parse(text)
        assert fields["title"] == "International Covenant on Civil and Political Rights"
        assert fields["opened_date"] == "16 December 1966"
        assert fields["volume"] == "999"
        assert fields["treaty_series"] == "UNTS"
        assert fields["start_page"] == "171"
        assert fields["force_date"] == "23 March 1976"
        assert fields["pinpoint"] is None

    def test_crc(self) -> None:
        text = (
            "Convention on the Rights of the Child, "
            "opened for signature 20 November 1989, "
            "1577 UNTS 3 (entered into force 2 September 1990)."
        )
        fields = self._parse(text)
        assert fields["title"] == "Convention on the Rights of the Child"
        assert fields["opened_date"] == "20 November 1989"
        assert fields["volume"] == "1577"
        assert fields["treaty_series"] == "UNTS"
        assert fields["start_page"] == "3"
        assert fields["force_date"] == "2 September 1990"

    def test_vienna_convention(self) -> None:
        text = (
            "Vienna Convention on the Law of Treaties, "
            "opened for signature 23 May 1969, "
            "1155 UNTS 331 (entered into force 27 January 1980)."
        )
        fields = self._parse(text)
        assert fields["title"] == "Vienna Convention on the Law of Treaties"
        assert fields["opened_date"] == "23 May 1969"
        assert fields["treaty_series"] == "UNTS"
        assert fields["force_date"] == "27 January 1980"

    def test_source_type_is_treaty(self) -> None:
        text = (
            "International Covenant on Civil and Political Rights, "
            "opened for signature 16 December 1966, "
            "999 UNTS 171 (entered into force 23 March 1976)."
        )
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.source_type == SourceType.TREATY
        assert result.confidence >= 0.8

    def test_title_italic_detection(self) -> None:
        title = "International Covenant on Civil and Political Rights"
        text = (
            f"{title}, "
            "opened for signature 16 December 1966, "
            "999 UNTS 171 (entered into force 23 March 1976)."
        )
        runs = [
            FootnoteRun(text=title, italic=True),
            FootnoteRun(
                text=", opened for signature 16 December 1966, "
                "999 UNTS 171 (entered into force 23 March 1976)."
            ),
        ]
        result = self.parser.parse(text, runs)
        assert result.fields["title_is_italic"] is True

    def test_title_not_italic_detection(self) -> None:
        text = (
            "International Covenant on Civil and Political Rights, "
            "opened for signature 16 December 1966, "
            "999 UNTS 171 (entered into force 23 March 1976)."
        )
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.fields["title_is_italic"] is False

    def test_refugee_convention(self) -> None:
        text = (
            "Convention Relating to the Status of Refugees, "
            "opened for signature 28 July 1951, "
            "189 UNTS 137 (entered into force 22 April 1954)."
        )
        fields = self._parse(text)
        assert fields["title"] == "Convention Relating to the Status of Refugees"
        assert fields["volume"] == "189"
        assert fields["start_page"] == "137"

    def test_unparseable_returns_unknown(self) -> None:
        runs = [FootnoteRun(text="Just some random text.")]
        result = self.parser.parse("Just some random text.", runs)
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0

    def test_partial_parse_with_opened_phrase(self) -> None:
        text = "Convention on Biodiversity, opened for signature 5 June 1992."
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.source_type == SourceType.TREATY
        assert result.confidence <= 0.6
        assert "parse_error" in result.fields

    def test_genocide_convention(self) -> None:
        text = (
            "Convention on the Prevention and Punishment of the Crime of Genocide, "
            "opened for signature 9 December 1948, "
            "78 UNTS 277 (entered into force 12 January 1951)."
        )
        fields = self._parse(text)
        assert fields["title"] == "Convention on the Prevention and Punishment of the Crime of Genocide"
        assert fields["opened_date"] == "9 December 1948"
        assert fields["volume"] == "78"
        assert fields["force_date"] == "12 January 1951"
