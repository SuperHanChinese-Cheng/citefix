"""Tests for Ibid and subsequent reference parsers (AGLC4 Rules 1.4.1 and 1.4.2)."""

from __future__ import annotations

import pytest

from citefix.models import FootnoteRun, SourceType
from citefix.parsers.ibid import IbidParser, SubsequentRefParser


@pytest.fixture
def ibid_parser() -> IbidParser:
    return IbidParser()


@pytest.fixture
def subsequent_ref_parser() -> SubsequentRefParser:
    return SubsequentRefParser()


# ---------------------------------------------------------------------------
# IbidParser — can_parse() tests
# ---------------------------------------------------------------------------


class TestIbidCanParse:
    def test_ibid_with_full_stop(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("Ibid.") == 0.95

    def test_ibid_with_pinpoint(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("Ibid 55.") == 0.95

    def test_ibid_lowercase(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("ibid") == 0.95

    def test_ibid_lowercase_with_full_stop(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("ibid.") == 0.95

    def test_id_variant(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("Id.") == 0.95

    def test_id_lowercase_variant(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("id.") == 0.95

    def test_ibid_no_match_on_case_citation(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("Mabo v Queensland (No 2) (1992) 175 CLR 1.") == 0.0

    def test_ibid_no_match_on_random_text(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("This is not a citation.") == 0.0

    def test_ibid_with_leading_whitespace(self, ibid_parser: IbidParser) -> None:
        assert ibid_parser.can_parse("  Ibid.  ") == 0.95


# ---------------------------------------------------------------------------
# IbidParser — parse() tests
# ---------------------------------------------------------------------------


class TestIbidParse:
    def test_ibid_plain(self, ibid_parser: IbidParser) -> None:
        """'Ibid.' with no pinpoint."""
        result = ibid_parser.parse("Ibid.", [FootnoteRun(text="Ibid.", italic=True)])
        assert result.source_type == SourceType.IBID
        assert result.confidence == 0.95
        assert result.fields["is_ibid"] is True
        assert result.fields["pinpoint"] is None
        assert result.fields["is_capitalised"] is True
        assert result.fields["has_full_stop"] is True
        assert result.fields["is_id_variant"] is False
        assert result.fields["is_italic"] is True

    def test_ibid_with_pinpoint(self, ibid_parser: IbidParser) -> None:
        """'Ibid 55.' should extract pinpoint=55."""
        result = ibid_parser.parse("Ibid 55.", [FootnoteRun(text="Ibid", italic=True),
                                                  FootnoteRun(text=" 55.")])
        assert result.source_type == SourceType.IBID
        assert result.fields["pinpoint"] == "55"
        assert result.fields["has_full_stop"] is True
        assert result.fields["is_capitalised"] is True

    def test_ibid_lowercase_no_fullstop(self, ibid_parser: IbidParser) -> None:
        """'ibid' lowercase without full stop — common error."""
        result = ibid_parser.parse("ibid", [FootnoteRun(text="ibid", italic=False)])
        assert result.source_type == SourceType.IBID
        assert result.fields["is_capitalised"] is False
        assert result.fields["has_full_stop"] is False
        assert result.fields["is_italic"] is False

    def test_id_variant_flagged(self, ibid_parser: IbidParser) -> None:
        """'Id.' should be detected and flagged as an id variant."""
        result = ibid_parser.parse("Id.", [FootnoteRun(text="Id.", italic=True)])
        assert result.source_type == SourceType.IBID
        assert result.fields["is_id_variant"] is True
        assert result.fields["keyword"] == "Id"
        assert result.fields["has_full_stop"] is True

    def test_ibid_not_italic(self, ibid_parser: IbidParser) -> None:
        """Ibid without italic formatting — error condition."""
        result = ibid_parser.parse("Ibid.", [FootnoteRun(text="Ibid.", italic=False)])
        assert result.source_type == SourceType.IBID
        assert result.fields["is_italic"] is False

    def test_ibid_with_bracket_pinpoint(self, ibid_parser: IbidParser) -> None:
        """'Ibid [31].' with paragraph pinpoint in square brackets."""
        result = ibid_parser.parse("Ibid [31].", [FootnoteRun(text="Ibid", italic=True),
                                                     FootnoteRun(text=" [31].")])
        assert result.source_type == SourceType.IBID
        assert result.fields["pinpoint"] == "[31]"
        assert result.fields["has_full_stop"] is True

    def test_ibid_with_range_pinpoint(self, ibid_parser: IbidParser) -> None:
        """'Ibid 42-45.' with page range."""
        result = ibid_parser.parse("Ibid 42-45.", [FootnoteRun(text="Ibid 42-45.", italic=True)])
        assert result.source_type == SourceType.IBID
        assert result.fields["pinpoint"] == "42-45"

    def test_ibid_parse_non_ibid_returns_unknown(self, ibid_parser: IbidParser) -> None:
        """Non-ibid text should return UNKNOWN with confidence 0.0."""
        result = ibid_parser.parse("Mabo v Queensland.", [])
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# SubsequentRefParser — can_parse() tests
# ---------------------------------------------------------------------------


class TestSubsequentRefCanParse:
    def test_simple_subsequent_ref(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        assert subsequent_ref_parser.can_parse("Mabo (n 3) 55.") == 0.90

    def test_subsequent_ref_no_pinpoint(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        assert subsequent_ref_parser.can_parse("Palmer (n 1).") == 0.90

    def test_subsequent_ref_with_section(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        assert subsequent_ref_parser.can_parse("Corporations Act (n 5) s 180.") == 0.90

    def test_no_match_on_ibid(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        assert subsequent_ref_parser.can_parse("Ibid.") == 0.0

    def test_no_match_on_case(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        assert subsequent_ref_parser.can_parse("Mabo v Queensland (No 2) (1992) 175 CLR 1.") == 0.0

    def test_fallback_partial_match(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        """Text with multiple (n X) refs still matches the full pattern (picks the last one)."""
        confidence = subsequent_ref_parser.can_parse("See generally Mabo (n 3) and Palmer (n 1).")
        assert confidence == 0.90


# ---------------------------------------------------------------------------
# SubsequentRefParser — parse() tests
# ---------------------------------------------------------------------------


class TestSubsequentRefParse:
    def test_case_subsequent_ref(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        """'Mabo (n 3) 55.' — case subsequent reference with pinpoint."""
        result = subsequent_ref_parser.parse(
            "Mabo (n 3) 55.",
            [FootnoteRun(text="Mabo", italic=True), FootnoteRun(text=" (n 3) 55.")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.confidence == 0.90
        assert result.fields["short_title"] == "Mabo"
        assert result.fields["footnote_ref"] == 3
        assert result.fields["pinpoint"] == "55"
        assert result.fields["has_full_stop"] is True

    def test_case_subsequent_ref_no_pinpoint(
        self, subsequent_ref_parser: SubsequentRefParser
    ) -> None:
        """'Palmer (n 1).' — no pinpoint."""
        result = subsequent_ref_parser.parse(
            "Palmer (n 1).",
            [FootnoteRun(text="Palmer", italic=True), FootnoteRun(text=" (n 1).")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.fields["short_title"] == "Palmer"
        assert result.fields["footnote_ref"] == 1
        assert result.fields["pinpoint"] is None
        assert result.fields["has_full_stop"] is True

    def test_legislation_subsequent_ref(
        self, subsequent_ref_parser: SubsequentRefParser
    ) -> None:
        """'Corporations Act (n 5) s 180.' — legislation with section pinpoint."""
        result = subsequent_ref_parser.parse(
            "Corporations Act (n 5) s 180.",
            [FootnoteRun(text="Corporations Act", italic=True),
             FootnoteRun(text=" (n 5) s 180.")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.fields["short_title"] == "Corporations Act"
        assert result.fields["footnote_ref"] == 5
        assert result.fields["pinpoint"] == "s 180"
        assert result.fields["has_full_stop"] is True

    def test_no_fullstop(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        """Missing full stop — common error."""
        result = subsequent_ref_parser.parse(
            "Mabo (n 3) 55",
            [FootnoteRun(text="Mabo (n 3) 55")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.fields["has_full_stop"] is False
        assert result.fields["pinpoint"] == "55"

    def test_large_footnote_ref(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        """Subsequent reference with large footnote number."""
        result = subsequent_ref_parser.parse(
            "McCutcheon (n 142) 920.",
            [FootnoteRun(text="McCutcheon (n 142) 920.")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.fields["short_title"] == "McCutcheon"
        assert result.fields["footnote_ref"] == 142
        assert result.fields["pinpoint"] == "920"

    def test_multi_word_short_title(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        """Short title with multiple words (common for legislation)."""
        result = subsequent_ref_parser.parse(
            "Fair Work Act (n 12) s 394.",
            [FootnoteRun(text="Fair Work Act", italic=True),
             FootnoteRun(text=" (n 12) s 394.")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.fields["short_title"] == "Fair Work Act"
        assert result.fields["footnote_ref"] == 12
        assert result.fields["pinpoint"] == "s 394"

    def test_parse_non_subsequent_ref_returns_unknown(
        self, subsequent_ref_parser: SubsequentRefParser
    ) -> None:
        """Non-subsequent-ref text should return UNKNOWN with confidence 0.0."""
        result = subsequent_ref_parser.parse("Ibid.", [])
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0

    def test_fallback_partial_parse(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        """Text with multiple (n X) refs matches the last one at full confidence."""
        result = subsequent_ref_parser.parse(
            "See generally Mabo (n 3) and Palmer (n 1).",
            [FootnoteRun(text="See generally Mabo (n 3) and Palmer (n 1).")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.confidence == 0.90
        assert result.fields["short_title"] == "See generally Mabo (n 3) and Palmer"
        assert result.fields["footnote_ref"] == 1
        assert result.fields["has_full_stop"] is True

    def test_bracket_pinpoint_subsequent(
        self, subsequent_ref_parser: SubsequentRefParser
    ) -> None:
        """Subsequent reference with paragraph pinpoint in square brackets."""
        result = subsequent_ref_parser.parse(
            "iiNet (n 7) [5].",
            [FootnoteRun(text="iiNet", italic=True), FootnoteRun(text=" (n 7) [5].")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.fields["short_title"] == "iiNet"
        assert result.fields["footnote_ref"] == 7
        assert result.fields["pinpoint"] == "[5]"
        assert result.fields["has_full_stop"] is True

    def test_no_space_in_n_ref(self, subsequent_ref_parser: SubsequentRefParser) -> None:
        """'(n3)' without space — common formatting variant."""
        result = subsequent_ref_parser.parse(
            "Mabo (n3) 55.",
            [FootnoteRun(text="Mabo (n3) 55.")],
        )
        assert result.source_type == SourceType.SUBSEQUENT_REF
        assert result.fields["short_title"] == "Mabo"
        assert result.fields["footnote_ref"] == 3
        assert result.fields["pinpoint"] == "55"
