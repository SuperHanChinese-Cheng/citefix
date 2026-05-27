"""Tests for the book and chapter citation parser (AGLC4 Rules 5.2 and 5.3)."""

from __future__ import annotations

from citefix.models import FootnoteRun, SourceType
from citefix.parsers.book import BookParser


# ═════════════════════════════════════════════════════════════════════════════
# can_parse() tests
# ═════════════════════════════════════════════════════════════════════════════


class TestBookParserCanParse:
    def setup_method(self) -> None:
        self.parser = BookParser()

    # ── Books ────────────────────────────────────────────────────────────────

    def test_simple_book_high_confidence(self) -> None:
        text = "Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) 45."
        assert self.parser.can_parse(text) >= 0.8

    def test_book_no_edition_high_confidence(self) -> None:
        text = "Michael Kirby, Judicial Activism (Sweet and Maxwell, 2004)."
        assert self.parser.can_parse(text) >= 0.8

    def test_book_multiple_authors(self) -> None:
        text = (
            "Robin Creyke, Matthew Groves and John McMillan, "
            "Control of Government Action: Text, Cases and Commentary "
            "(LexisNexis Butterworths, 5th ed, 2019) 420."
        )
        assert self.parser.can_parse(text) >= 0.8

    # ── Chapters ─────────────────────────────────────────────────────────────

    def test_chapter_high_confidence(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' in Andrew Stewart et al (eds), "
            "Creighton and Stewart's Labour Law (Federation Press, 6th ed, 2016) 1, 15."
        )
        assert self.parser.can_parse(text) >= 0.9

    # ── Non-books ────────────────────────────────────────────────────────────

    def test_case_citation_zero(self) -> None:
        text = "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42."
        assert self.parser.can_parse(text) < 0.5

    def test_legislation_zero(self) -> None:
        text = "Corporations Act 2001 (Cth) s 180(1)."
        assert self.parser.can_parse(text) < 0.3

    def test_random_text_zero(self) -> None:
        assert self.parser.can_parse("Some random sentence.") == 0.0


# ═════════════════════════════════════════════════════════════════════════════
# parse() tests — Books (Rule 5.2)
# ═════════════════════════════════════════════════════════════════════════════


class TestBookParserParse:
    def setup_method(self) -> None:
        self.parser = BookParser()

    def _parse(self, text: str, italic_text: str | None = None) -> dict:
        """Parse *text* and return the fields dict.

        If *italic_text* is provided, it is split into a separate italic run.
        """
        if italic_text:
            idx = text.find(italic_text)
            runs: list[FootnoteRun] = []
            if idx > 0:
                runs.append(FootnoteRun(text=text[:idx]))
            runs.append(FootnoteRun(text=italic_text, italic=True))
            rest = text[idx + len(italic_text) :]
            if rest:
                runs.append(FootnoteRun(text=rest))
        else:
            runs = [FootnoteRun(text=text)]
        return self.parser.parse(text, runs).fields

    def _parse_result(self, text: str) -> "ParseResult":  # noqa: F821
        runs = [FootnoteRun(text=text)]
        return self.parser.parse(text, runs)

    # ── 1. Simple book with edition and pinpoint ─────────────────────────────

    def test_simple_book(self) -> None:
        fields = self._parse(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) 45."
        )
        assert fields["author"] == "Mark Leeming"
        assert fields["title"] == "Authority to Decide"
        assert fields["publisher"] == "Federation Press"
        assert fields["edition"] == "2nd ed"
        assert fields["year"] == "2020"
        assert fields["pinpoint"] == "45"
        assert fields["is_chapter"] is False
        assert fields["has_edition_error"] is False
        assert fields["has_double_quotes"] is False
        assert fields["has_pinpoint_prefix"] is False

    # ── 2. Book without edition ──────────────────────────────────────────────

    def test_book_no_edition(self) -> None:
        fields = self._parse(
            "Michael Kirby, Judicial Activism (Sweet and Maxwell, 2004)."
        )
        assert fields["author"] == "Michael Kirby"
        assert fields["title"] == "Judicial Activism"
        assert fields["publisher"] == "Sweet and Maxwell"
        assert fields["edition"] is None
        assert fields["year"] == "2004"
        assert fields["pinpoint"] is None
        assert fields["is_chapter"] is False

    # ── 3. Multiple authors ──────────────────────────────────────────────────

    def test_multiple_authors(self) -> None:
        fields = self._parse(
            "Robin Creyke, Matthew Groves and John McMillan, "
            "Control of Government Action: Text, Cases and Commentary "
            "(LexisNexis Butterworths, 5th ed, 2019) 420."
        )
        assert fields["author"] == "Robin Creyke, Matthew Groves and John McMillan"
        assert "Control of Government Action" in fields["title"]
        assert fields["publisher"] == "LexisNexis Butterworths"
        assert fields["edition"] == "5th ed"
        assert fields["year"] == "2019"
        assert fields["pinpoint"] == "420"

    # ── 4. Book with "edition" spelled out (error) ───────────────────────────

    def test_edition_error_detected(self) -> None:
        fields = self._parse(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd edition, 2020) 45."
        )
        assert fields["has_edition_error"] is True
        assert fields["edition"] == "2nd ed"  # normalised

    # ── 5. Book with "edn" abbreviation (error) ─────────────────────────────

    def test_edn_error_detected(self) -> None:
        fields = self._parse(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd edn, 2020) 45."
        )
        assert fields["has_edition_error"] is True

    # ── 6. Book title in double quotes (error) ──────────────────────────────

    def test_double_quotes_on_title(self) -> None:
        fields = self._parse(
            'Mark Leeming, "Authority to Decide" (Federation Press, 2nd ed, 2020) 45.'
        )
        assert fields["has_double_quotes"] is True
        assert fields["title"] == "Authority to Decide"

    # ── 7. Pinpoint with "p" prefix (error) ─────────────────────────────────

    def test_pinpoint_prefix_p(self) -> None:
        fields = self._parse(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) p 45."
        )
        assert fields["has_pinpoint_prefix"] is True
        assert fields["pinpoint"] == "45"

    # ── 8. Pinpoint with "p." prefix (error) ────────────────────────────────

    def test_pinpoint_prefix_p_dot(self) -> None:
        fields = self._parse(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) p. 45."
        )
        assert fields["has_pinpoint_prefix"] is True
        assert fields["pinpoint"] == "45"

    # ── 9. Book with page range pinpoint ─────────────────────────────────────

    def test_pinpoint_range(self) -> None:
        fields = self._parse(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) 45-50."
        )
        assert fields["pinpoint"] == "45-50"

    # ── 10. Source type is BOOK ──────────────────────────────────────────────

    def test_source_type_book(self) -> None:
        result = self._parse_result(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) 45."
        )
        assert result.source_type == SourceType.BOOK

    # ── 11. Title italic detection ───────────────────────────────────────────

    def test_title_italic_detected(self) -> None:
        fields = self._parse(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) 45.",
            italic_text="Authority to Decide",
        )
        assert fields["title_is_italic"] is True

    def test_title_not_italic(self) -> None:
        fields = self._parse(
            "Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) 45."
        )
        assert fields["title_is_italic"] is False

    # ── 12. First edition (1st ed) ───────────────────────────────────────────

    def test_first_edition(self) -> None:
        fields = self._parse(
            "John Smith, Contract Law (Oxford University Press, 1st ed, 2010) 12."
        )
        assert fields["edition"] == "1st ed"
        assert fields["has_edition_error"] is False

    # ── 13. Third edition ────────────────────────────────────────────────────

    def test_third_edition(self) -> None:
        fields = self._parse(
            "Jane Doe, Equity and Trusts (Cambridge University Press, 3rd ed, 2015)."
        )
        assert fields["edition"] == "3rd ed"
        assert fields["pinpoint"] is None

    # ── 14. Multiple combined errors ─────────────────────────────────────────

    def test_book_all_errors(self) -> None:
        """Double quotes, 'edition' not abbreviated, 'p' in pinpoint."""
        fields = self._parse(
            'Mark Leeming, "Authority to Decide" (Federation Press, 2nd edition, 2020) p 45.'
        )
        assert fields["has_double_quotes"] is True
        assert fields["has_edition_error"] is True
        assert fields["has_pinpoint_prefix"] is True
        assert fields["pinpoint"] == "45"
        assert fields["edition"] == "2nd ed"


# ═════════════════════════════════════════════════════════════════════════════
# parse() tests — Chapters in Edited Books (Rule 5.3)
# ═════════════════════════════════════════════════════════════════════════════


class TestChapterParserParse:
    def setup_method(self) -> None:
        self.parser = BookParser()

    def _parse(self, text: str) -> dict:
        runs = [FootnoteRun(text=text)]
        return self.parser.parse(text, runs).fields

    def _parse_result(self, text: str) -> "ParseResult":  # noqa: F821
        runs = [FootnoteRun(text=text)]
        return self.parser.parse(text, runs)

    # ── 15. Standard chapter in edited book ──────────────────────────────────

    def test_chapter_basic(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' in Andrew Stewart et al (eds), "
            "Creighton and Stewart's Labour Law (Federation Press, 6th ed, 2016) 1, 15."
        )
        fields = self._parse(text)
        assert fields["is_chapter"] is True
        assert fields["author"] == "Andrew Stewart"
        assert fields["chapter_title"] == "The Evolution of Labour Law"
        assert fields["editor"] == "Andrew Stewart et al"
        assert fields["ed_marker"] == "eds"
        assert "Labour Law" in fields["title"]
        assert fields["publisher"] == "Federation Press"
        assert fields["edition"] == "6th ed"
        assert fields["year"] == "2016"
        assert fields["start_page"] == "1"
        assert fields["pinpoint"] == "15"

    # ── 16. Source type is CHAPTER ───────────────────────────────────────────

    def test_source_type_chapter(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' in Andrew Stewart et al (eds), "
            "Creighton and Stewart's Labour Law (Federation Press, 6th ed, 2016) 1, 15."
        )
        result = self._parse_result(text)
        assert result.source_type == SourceType.CHAPTER

    # ── 17. Chapter with single editor (ed) ──────────────────────────────────

    def test_chapter_single_editor(self) -> None:
        text = (
            "Jane Doe, 'Modern Remedies' in John Smith (ed), "
            "Equity and Trusts (Oxford University Press, 2nd ed, 2018) 100, 115."
        )
        fields = self._parse(text)
        assert fields["ed_marker"] == "ed"
        assert fields["editor"] == "John Smith"
        assert fields["start_page"] == "100"
        assert fields["pinpoint"] == "115"

    # ── 18. Chapter with double quotes (error) ──────────────────────────────

    def test_chapter_double_quotes_error(self) -> None:
        text = (
            'Andrew Stewart, "The Evolution of Labour Law" in Andrew Stewart et al (eds), '
            "Creighton and Stewart's Labour Law (Federation Press, 6th ed, 2016) 1, 15."
        )
        fields = self._parse(text)
        assert fields["has_double_quotes"] is True
        assert fields["chapter_title"] == "The Evolution of Labour Law"

    # ── 19. Chapter with edition error ───────────────────────────────────────

    def test_chapter_edition_error(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' in Andrew Stewart et al (eds), "
            "Creighton and Stewart's Labour Law (Federation Press, 6th edition, 2016) 1."
        )
        fields = self._parse(text)
        assert fields["has_edition_error"] is True
        assert fields["edition"] == "6th ed"

    # ── 20. Chapter without pinpoint (only start page) ───────────────────────

    def test_chapter_no_pinpoint(self) -> None:
        text = (
            "Jane Doe, 'Modern Remedies' in John Smith (ed), "
            "Equity and Trusts (Oxford University Press, 2nd ed, 2018) 100."
        )
        fields = self._parse(text)
        assert fields["start_page"] == "100"
        assert fields["pinpoint"] is None

    # ── 21. Chapter without edition ──────────────────────────────────────────

    def test_chapter_no_edition(self) -> None:
        text = (
            "Jane Doe, 'Negligence Today' in John Smith (ed), "
            "Tort Law (Hart Publishing, 2020) 50, 60."
        )
        fields = self._parse(text)
        assert fields["edition"] is None
        assert fields["has_edition_error"] is False
        assert fields["year"] == "2020"
        assert fields["start_page"] == "50"
        assert fields["pinpoint"] == "60"

