"""Tests for introductory signal stripping (AGLC4 Rule 1.2)."""

from __future__ import annotations

import pytest

from citefix.signals import strip_introductory_signal


class TestStripIntroductorySignal:
    """Unit tests for the strip_introductory_signal utility."""

    def test_no_signal(self) -> None:
        signal, text = strip_introductory_signal("Mabo v Queensland (No 2) (1992) 175 CLR 1.")
        assert signal == ""
        assert text == "Mabo v Queensland (No 2) (1992) 175 CLR 1."

    def test_see(self) -> None:
        signal, text = strip_introductory_signal("See Mabo v Queensland (No 2) (1992) 175 CLR 1.")
        assert signal == "See"
        assert text == "Mabo v Queensland (No 2) (1992) 175 CLR 1."

    def test_see_also(self) -> None:
        signal, text = strip_introductory_signal(
            "See also Palmer v Ayres [2017] HCA 5, [31]."
        )
        assert signal == "See also"
        assert text == "Palmer v Ayres [2017] HCA 5, [31]."

    def test_see_eg(self) -> None:
        signal, text = strip_introductory_signal(
            "See eg Smith v Jones [2023] NSWSC 456."
        )
        assert signal == "See eg"
        assert text == "Smith v Jones [2023] NSWSC 456."

    def test_see_eg_with_comma(self) -> None:
        signal, text = strip_introductory_signal(
            "See, eg, Smith v Jones [2023] NSWSC 456."
        )
        assert signal == "See, eg,"
        assert text == "Smith v Jones [2023] NSWSC 456."

    def test_see_especially(self) -> None:
        signal, text = strip_introductory_signal(
            "See especially Mabo v Queensland (No 2) (1992) 175 CLR 1, 42."
        )
        assert signal == "See especially"
        assert text == "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42."

    def test_see_generally(self) -> None:
        signal, text = strip_introductory_signal(
            "See generally Jani McCutcheon, 'The Vanishing Author' (2013) 36 UNSWLJ 915."
        )
        assert signal == "See generally"
        assert text == "Jani McCutcheon, 'The Vanishing Author' (2013) 36 UNSWLJ 915."

    def test_but_see(self) -> None:
        signal, text = strip_introductory_signal(
            "But see Palmer v Ayres [2017] HCA 5."
        )
        assert signal == "But see"
        assert text == "Palmer v Ayres [2017] HCA 5."

    def test_cf(self) -> None:
        signal, text = strip_introductory_signal(
            "Cf Mabo v Queensland (No 2) (1992) 175 CLR 1, 42."
        )
        assert signal == "Cf"
        assert text == "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42."

    def test_cf_lowercase(self) -> None:
        signal, text = strip_introductory_signal(
            "cf Mabo v Queensland (No 2) (1992) 175 CLR 1."
        )
        assert signal == "cf"
        assert text == "Mabo v Queensland (No 2) (1992) 175 CLR 1."

    def test_see_ibid(self) -> None:
        """Signal before Ibid should be stripped correctly."""
        signal, text = strip_introductory_signal("See Ibid 55.")
        assert signal == "See"
        assert text == "Ibid 55."

    def test_see_at_start_of_parties_not_stripped(self) -> None:
        """Words like 'Secretary' should NOT be stripped as signals."""
        signal, text = strip_introductory_signal(
            "Secretary of State v Smith [2020] NZSC 10."
        )
        assert signal == ""
        assert text == "Secretary of State v Smith [2020] NZSC 10."

    def test_whitespace_preserved(self) -> None:
        """Leading whitespace in the remaining text should be handled."""
        signal, text = strip_introductory_signal("  See   Mabo v Queensland (1992) 175 CLR 1.")
        assert signal == "See"
        assert text == "Mabo v Queensland (1992) 175 CLR 1."

    def test_see_legislation(self) -> None:
        signal, text = strip_introductory_signal(
            "See Corporations Act 2001 (Cth) s 180(1)."
        )
        assert signal == "See"
        assert text == "Corporations Act 2001 (Cth) s 180(1)."

    def test_empty_text(self) -> None:
        signal, text = strip_introductory_signal("")
        assert signal == ""
        assert text == ""
