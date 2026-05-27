"""Tests for the journal article citation parser."""

from __future__ import annotations

import pytest

from citefix.models import FootnoteRun, SourceType
from citefix.parsers.journal import JournalArticleParser


class TestJournalParserCanParse:
    def setup_method(self) -> None:
        self.parser = JournalArticleParser()

    def test_correct_citation_high_confidence(self) -> None:
        text = (
            "Jani McCutcheon, 'The Vanishing Author in Computer-Generated Works' "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        assert self.parser.can_parse(text) >= 0.9

    def test_citation_with_pinpoint_high_confidence(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100, 115."
        )
        assert self.parser.can_parse(text) >= 0.9

    def test_double_quoted_title_still_detectable(self) -> None:
        text = (
            'Jani McCutcheon, "The Vanishing Author" '
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        assert self.parser.can_parse(text) >= 0.9

    def test_case_citation_low_confidence(self) -> None:
        assert self.parser.can_parse("Mabo v Queensland (1992) 175 CLR 1.") < 0.3

    def test_legislation_low_confidence(self) -> None:
        assert self.parser.can_parse("Corporations Act 2001 (Cth) s 180(1).") < 0.3

    def test_random_text_zero(self) -> None:
        assert self.parser.can_parse("Some random sentence about nothing.") == 0.0

    def test_ibid_zero(self) -> None:
        assert self.parser.can_parse("Ibid 42.") == 0.0

    def test_signal_pattern_medium_confidence(self) -> None:
        """A citation with odd formatting but clear journal-like signals."""
        text = (
            "Author Name 'Some Title' "
            "(2020) 10 Some Journal 50."
        )
        # This may not match the full structured pattern due to missing comma after author,
        # but the signal pattern should catch it.
        conf = self.parser.can_parse(text)
        assert conf >= 0.5


class TestJournalParserParse:
    def setup_method(self) -> None:
        self.parser = JournalArticleParser()

    def _parse(self, text: str, italic_text: str | None = None) -> dict:
        runs = [FootnoteRun(text=text)]
        if italic_text:
            # Build runs with the italic_text portion marked as italic
            idx = text.find(italic_text)
            if idx >= 0:
                runs = []
                if idx > 0:
                    runs.append(FootnoteRun(text=text[:idx]))
                runs.append(FootnoteRun(text=italic_text, italic=True))
                rest = text[idx + len(italic_text):]
                if rest:
                    runs.append(FootnoteRun(text=rest))
        result = self.parser.parse(text, runs)
        return result.fields

    # ----- Correct citations -----

    def test_mccutcheon_full_citation(self) -> None:
        text = (
            "Jani McCutcheon, 'The Vanishing Author in Computer-Generated Works' "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        fields = self._parse(text)
        assert fields["author"] == "Jani McCutcheon"
        assert fields["title"] == "The Vanishing Author in Computer-Generated Works"
        assert fields["year"] == "2013"
        assert fields["volume"] == "36"
        assert fields["journal_name"] == "University of New South Wales Law Journal"
        assert fields["start_page"] == "915"
        assert fields["pinpoint"] is None
        assert fields["has_double_quotes"] is False
        assert fields["has_surname_first"] is False

    def test_stewart_with_pinpoint(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100, 115."
        )
        fields = self._parse(text)
        assert fields["author"] == "Andrew Stewart"
        assert fields["title"] == "The Evolution of Labour Law"
        assert fields["year"] == "2019"
        assert fields["volume"] == "42"
        assert fields["journal_name"] == "Melbourne University Law Review"
        assert fields["start_page"] == "100"
        assert fields["pinpoint"] == "115"

    def test_two_authors(self) -> None:
        text = (
            "Rosemary Owens and Joellen Riley, 'The Challenge of Insecure Work' "
            "(2007) 20 Australian Journal of Labour Law 162."
        )
        fields = self._parse(text)
        assert fields["author"] == "Rosemary Owens and Joellen Riley"
        assert fields["has_surname_first"] is False

    def test_three_authors(self) -> None:
        text = (
            "Robin Creyke, Matthew Groves and John McMillan, 'Judicial Review Outcomes' "
            "(2018) 25 Australian Journal of Administrative Law 82."
        )
        fields = self._parse(text)
        assert fields["author"] == "Robin Creyke, Matthew Groves and John McMillan"
        assert fields["has_surname_first"] is False

    def test_adelaide_law_review(self) -> None:
        text = (
            "John Williams, 'The Emergence of the Commonwealth Constitution' "
            "(2000) 21 Adelaide Law Review 55."
        )
        fields = self._parse(text)
        assert fields["journal_name"] == "Adelaide Law Review"
        assert fields["has_abbreviated_journal"] is False

    def test_federal_law_review(self) -> None:
        text = (
            "Lisa Burton Crawford, 'The Rule of Law in Parliament' "
            "(2021) 49 Federal Law Review 65."
        )
        fields = self._parse(text)
        assert fields["journal_name"] == "Federal Law Review"
        assert fields["start_page"] == "65"

    # ----- Error detection: double quotes -----

    def test_detects_double_quotes(self) -> None:
        text = (
            'Jani McCutcheon, "The Vanishing Author in Computer-Generated Works" '
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        fields = self._parse(text)
        assert fields["has_double_quotes"] is True

    def test_correct_single_quotes_no_error(self) -> None:
        text = (
            "Jani McCutcheon, 'The Vanishing Author in Computer-Generated Works' "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        fields = self._parse(text)
        assert fields["has_double_quotes"] is False

    def test_detects_smart_double_quotes(self) -> None:
        text = (
            "Jani McCutcheon, “The Vanishing Author” "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        fields = self._parse(text)
        assert fields["has_double_quotes"] is True

    def test_smart_single_quotes_no_error(self) -> None:
        text = (
            "Jani McCutcheon, ‘The Vanishing Author’ "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        fields = self._parse(text)
        assert fields["has_double_quotes"] is False

    # ----- Error detection: surname-first author -----

    def test_detects_surname_first_author(self) -> None:
        text = (
            "McCutcheon, Jani, 'The Vanishing Author in Computer-Generated Works' "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        fields = self._parse(text)
        assert fields["has_surname_first"] is True

    def test_surname_first_two_authors(self) -> None:
        text = (
            "Stewart, Andrew and Riley, Joellen, 'Labour Law Reform' "
            "(2019) 42 Melbourne University Law Review 100."
        )
        fields = self._parse(text)
        assert fields["has_surname_first"] is True

    def test_correct_author_order_no_error(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100."
        )
        fields = self._parse(text)
        assert fields["has_surname_first"] is False

    # ----- Error detection: abbreviated journal -----

    def test_detects_abbreviated_journal_known(self) -> None:
        text = (
            "Jani McCutcheon, 'The Vanishing Author' "
            "(2013) 36 UNSWLJ 915."
        )
        fields = self._parse(text)
        assert fields["has_abbreviated_journal"] is True

    def test_detects_abbreviated_journal_uppercase_heuristic(self) -> None:
        text = (
            "Andrew Stewart, 'Labour Law Reform' "
            "(2019) 42 MULR 100."
        )
        fields = self._parse(text)
        assert fields["has_abbreviated_journal"] is True

    def test_full_journal_name_no_error(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100."
        )
        fields = self._parse(text)
        assert fields["has_abbreviated_journal"] is False

    # ----- Error detection: "at p." pinpoint -----

    def test_detects_at_p_pinpoint(self) -> None:
        text = (
            "Jani McCutcheon, 'The Vanishing Author' "
            "(2013) 36 University of New South Wales Law Journal 915, at p. 920."
        )
        fields = self._parse(text)
        assert fields["has_at_p_pinpoint"] is True
        assert fields["pinpoint"] == "920"

    def test_detects_p_pinpoint(self) -> None:
        text = (
            "Jani McCutcheon, 'The Vanishing Author' "
            "(2013) 36 University of New South Wales Law Journal 915, p 920."
        )
        fields = self._parse(text)
        assert fields["has_at_p_pinpoint"] is True

    def test_clean_pinpoint_no_error(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100, 115."
        )
        fields = self._parse(text)
        assert fields["has_at_p_pinpoint"] is False

    # ----- Error detection: missing full stop -----

    def test_missing_full_stop(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100, 115"
        )
        fields = self._parse(text)
        assert fields["has_trailing_dot"] is False

    def test_has_trailing_dot(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100, 115."
        )
        fields = self._parse(text)
        assert fields["has_trailing_dot"] is True

    # ----- Error detection: pinpoint hyphen -----

    def test_detects_pinpoint_hyphen(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100, 115-120."
        )
        fields = self._parse(text)
        assert fields["has_pinpoint_hyphen"] is True
        assert fields["pinpoint"] == "115-120"

    def test_en_dash_no_error(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100, 115–120."
        )
        fields = self._parse(text)
        assert fields["has_pinpoint_hyphen"] is False

    # ----- Error detection: italic journal name -----

    def test_journal_italic_detected(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100."
        )
        fields = self._parse(text, italic_text="Melbourne University Law Review")
        assert fields["journal_is_italic"] is True

    def test_journal_not_italic(self) -> None:
        text = (
            "Andrew Stewart, 'The Evolution of Labour Law' "
            "(2019) 42 Melbourne University Law Review 100."
        )
        fields = self._parse(text)
        assert fields["journal_is_italic"] is False

    # ----- Source type -----

    def test_source_type_is_journal(self) -> None:
        text = (
            "Jani McCutcheon, 'The Vanishing Author in Computer-Generated Works' "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.source_type == SourceType.JOURNAL_ARTICLE
        assert result.confidence >= 0.9

    def test_unparseable_returns_unknown(self) -> None:
        text = "Some random text that is not a citation."
        runs = [FootnoteRun(text=text)]
        result = self.parser.parse(text, runs)
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0

    # ----- Edge cases -----

    def test_monash_university_law_review(self) -> None:
        text = (
            "Wendy Lacey, 'Inherent Jurisdiction and Judicial Review' "
            "(2003) 29 Monash University Law Review 187."
        )
        fields = self._parse(text)
        assert fields["journal_name"] == "Monash University Law Review"
        assert fields["volume"] == "29"

    def test_sydney_law_review(self) -> None:
        text = (
            "Rosalind Dixon, 'The Functional Constitution' "
            "(2015) 37 Sydney Law Review 301."
        )
        fields = self._parse(text)
        assert fields["journal_name"] == "Sydney Law Review"

    def test_alternative_law_journal(self) -> None:
        text = (
            "Margaret Thornton, 'The Flexible Cyborg' "
            "(2005) 30 Alternative Law Journal 56."
        )
        fields = self._parse(text)
        assert fields["journal_name"] == "Alternative Law Journal"

    def test_combined_errors_citation(self) -> None:
        """A citation with multiple AGLC4 errors simultaneously."""
        text = (
            'McCutcheon, Jani, "The Vanishing Author" '
            "(2013) 36 UNSWLJ 915, at p. 920."
        )
        fields = self._parse(text)
        assert fields["has_surname_first"] is True
        assert fields["has_double_quotes"] is True
        assert fields["has_abbreviated_journal"] is True
        assert fields["has_at_p_pinpoint"] is True

    def test_no_pinpoint(self) -> None:
        text = (
            "Jani McCutcheon, 'The Vanishing Author' "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        fields = self._parse(text)
        assert fields["pinpoint"] is None

    def test_title_with_colon(self) -> None:
        """Titles containing colons and other punctuation should parse correctly."""
        text = (
            "Peta Spender, 'Guns and Roses: The Impact of Mass Tort Class Actions' "
            "(2005) 23 University of Queensland Law Journal 437."
        )
        fields = self._parse(text)
        assert fields["title"] == "Guns and Roses: The Impact of Mass Tort Class Actions"
        assert fields["year"] == "2005"
        assert fields["volume"] == "23"
        assert fields["journal_name"] == "University of Queensland Law Journal"

    def test_hyphenated_author_surname(self) -> None:
        """Authors with hyphenated surnames should parse correctly."""
        text = (
            "Anne-Marie Boxall, 'Health Policy Reform in Australia' "
            "(2011) 34 University of New South Wales Law Journal 780."
        )
        fields = self._parse(text)
        assert fields["author"] == "Anne-Marie Boxall"
        assert fields["has_surname_first"] is False

    def test_issue_number_captured(self) -> None:
        """Issue number in parentheses after volume should be parsed."""
        text = (
            "Andrew Edgar, 'Administrative Regulation-Making' "
            "(2017) 40(3) Melbourne University Law Review 738."
        )
        fields = self._parse(text)
        assert fields["volume"] == "40"
        assert fields["issue"] == "3"
        assert fields["journal_name"] == "Melbourne University Law Review"
        assert fields["start_page"] == "738"

    def test_no_issue_number(self) -> None:
        """Citations without issue number should have issue=None."""
        text = (
            "Jani McCutcheon, 'The Vanishing Author' "
            "(2013) 36 University of New South Wales Law Journal 915."
        )
        fields = self._parse(text)
        assert fields["volume"] == "36"
        assert fields["issue"] is None

    def test_square_bracket_year(self) -> None:
        """Year-organized journals use square brackets per rule 5.3."""
        text = (
            "CB Cato, 'The Mareva Injunction and Its Application in New Zealand' "
            "[1980] 12 New Zealand Law Journal 270."
        )
        result = self.parser.parse(text, [])
        assert result.source_type == SourceType.JOURNAL_ARTICLE
        assert result.fields["year"] == "1980"
        assert result.fields["year_bracket"] == "square"

    def test_initial_periods_detected(self) -> None:
        """Author initials with periods should be flagged."""
        text = (
            "R.J. Ellicott, 'The Autochthonous Expedient' "
            "(2008) 82 Australian Law Journal 700."
        )
        fields = self._parse(text)
        assert fields["has_initial_periods"] is True

    def test_clean_initials_no_flag(self) -> None:
        """Author initials without periods should not be flagged."""
        text = (
            "RJ Ellicott, 'The Autochthonous Expedient' "
            "(2008) 82 Australian Law Journal 700."
        )
        fields = self._parse(text)
        assert fields["has_initial_periods"] is False

    def test_the_prefix_detected(self) -> None:
        """Journal names starting with 'The' should be flagged."""
        text = (
            "Author Name, 'Some Title' "
            "(2020) 40 The Australian Law Journal 100."
        )
        fields = self._parse(text)
        assert fields["has_the_prefix"] is True
        assert fields["journal_name"] == "The Australian Law Journal"

    def test_no_the_prefix(self) -> None:
        """Journal names without 'The' prefix should not be flagged."""
        text = (
            "Author Name, 'Some Title' "
            "(2020) 40 Australian Law Journal 100."
        )
        fields = self._parse(text)
        assert fields["has_the_prefix"] is False
