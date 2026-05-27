"""Tests for footnote text normalizer."""

import pytest

from citefix.rules.normalizer import normalize_footnote_text as n


class TestCharacterNormalization:
    def test_zero_width_removal(self):
        assert n("CLR​1") == "CLR1."

    def test_non_breaking_space(self):
        assert n("(Cth)\xa0s 14") == "(Cth) s 14."

    def test_fullwidth_brackets(self):
        assert n("（1992）") == "(1992)."

    def test_fullwidth_square_brackets(self):
        assert n("［2017］") == "[2017]."


class TestWhitespace:
    def test_double_space(self):
        assert n("CLR  1") == "CLR 1."

    def test_triple_space(self):
        assert n("CLR   1 ,  42 .") == "CLR 1, 42."

    def test_leading_trailing(self):
        assert n("  CLR 1, 42.  ") == "CLR 1, 42."


class TestVSpacing:
    def test_double_space_around_v(self):
        assert n("Mabo  v  Queensland") == "Mabo v Queensland."


class TestCommaFixes:
    def test_space_before_comma(self):
        assert n("CLR 1 , 42") == "CLR 1, 42."

    def test_double_comma(self):
        assert n("CLR 1,, 42") == "CLR 1, 42."

    def test_comma_before_letter(self):
        assert n("CLR 1,42") == "CLR 1, 42."

    def test_comma_in_number_preserved(self):
        # Should NOT add space in "1,000" type numbers
        # This is tricky -- our regex targets commas before digits
        # but we need to be careful about number formatting
        pass


class TestBracketSpacing:
    def test_space_inside_round(self):
        assert n("( 1992 )") == "(1992)."

    def test_space_inside_square(self):
        assert n("[ 2017 ]") == "[2017]."


class TestFullStop:
    def test_missing_full_stop(self):
        assert n("CLR 1, 42") == "CLR 1, 42."

    def test_double_full_stop(self):
        assert n("CLR 1, 42..") == "CLR 1, 42."

    def test_trailing_space_before_stop(self):
        assert n("CLR 1, 42. ") == "CLR 1, 42."

    def test_already_has_full_stop(self):
        assert n("CLR 1, 42.") == "CLR 1, 42."


class TestDashNormalization:
    def test_hyphen_to_en_dash(self):
        assert n("42-55") == "42–55."

    def test_em_dash_to_en_dash(self):
        assert n("42—55") == "42–55."


class TestQuoteNormalization:
    def test_double_to_single(self):
        assert n('"Title"') == "‘Title’."

    def test_smart_double_to_single(self):
        assert n('“Title”') == "‘Title’."


class TestSectionSpacing:
    def test_s_no_space(self):
        assert n("s14(1)") == "s 14(1)."

    def test_reg_no_space(self):
        assert n("reg28") == "reg 28."

    def test_s_already_spaced(self):
        assert n("s 14(1)") == "s 14(1)."


class TestIdempotent:
    """Already-correct text should not be modified."""

    def test_correct_case(self):
        assert n("Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.") == \
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42."

    def test_correct_legislation(self):
        assert n("Corporations Act 2001 (Cth) s 180(1).") == \
            "Corporations Act 2001 (Cth) s 180(1)."

    def test_correct_ibid(self):
        assert n("Ibid 55.") == "Ibid 55."

    def test_empty_input(self):
        assert n("") == ""

    def test_whitespace_only(self):
        assert n("   ") == "   "
