"""Tests for section-before-title detector."""
import pytest
from citefix.rules.validators import detect_section_before_title, reorder_section_after_title


class TestDetectSectionBeforeTitle:
    def test_section_before_act(self):
        assert detect_section_before_title("s 31A Federal Court of Australia Act 1976 (Cth)") is True

    def test_section_after_act(self):
        assert detect_section_before_title("Federal Court of Australia Act 1976 (Cth) s 31A") is False

    def test_correct_order(self):
        assert detect_section_before_title("Corporations Act 2001 (Cth) s 180(1)") is False

    def test_section_before_with_jurisdiction(self):
        assert detect_section_before_title("s 14 Limitation Act 2005 (WA)") is True

    def test_regulation_before_rules(self):
        assert detect_section_before_title("reg 42 Legal Profession Uniform General Rules 2015 (NSW)") is True


class TestReorderSectionAfterTitle:
    def test_reorder_federal_act(self):
        result = reorder_section_after_title("s 31A Federal Court of Australia Act 1976 (Cth)")
        assert result == "Federal Court of Australia Act 1976 (Cth) s 31A"

    def test_reorder_with_subsection(self):
        result = reorder_section_after_title("s 14(1) Limitation Act 2005 (WA)")
        assert result == "Limitation Act 2005 (WA) s 14(1)"

    def test_no_reorder_correct_order(self):
        text = "Corporations Act 2001 (Cth) s 180(1)"
        assert reorder_section_after_title(text) == text
