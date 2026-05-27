"""Tests for AGLC4 reference data module and its wrappers."""

from __future__ import annotations

import pytest

from citefix.rules.reference_data import (
    COURT_IDENTIFIERS,
    JOURNAL_ABBREVIATIONS,
    JURISDICTION_FULL_TO_ABBR,
    PINPOINT_CORRECTIONS,
    REPORT_SERIES,
    get_bracket_type,
    is_medium_neutral,
)
from citefix.rules.abbreviations import (
    ALL_REPORT_SERIES,
    MEDIUM_NEUTRAL_IDENTIFIERS,
    ROUND_BRACKET_SERIES,
    SQUARE_BRACKET_SERIES,
    BracketType,
    get_bracket_type as abbr_get_bracket_type,
    is_medium_neutral as abbr_is_medium_neutral,
)
from citefix.rules.jurisdictions import (
    FULL_NAME_TO_ABBREVIATION,
    JURISDICTION_ABBREVIATIONS,
    SECTION_ABBREVIATIONS,
    VALID_JURISDICTIONS,
)


class TestReferenceData:
    def test_clr_round_brackets(self) -> None:
        assert get_bracket_type("CLR") == "round"

    def test_hca_square_brackets(self) -> None:
        assert get_bracket_type("HCA") == "square"

    def test_nswlr_round_brackets(self) -> None:
        assert get_bracket_type("NSWLR") == "round"

    def test_wasc_square_brackets(self) -> None:
        assert get_bracket_type("WASC") == "square"

    def test_fca_medium_neutral(self) -> None:
        assert is_medium_neutral("FCA") is True

    def test_clr_not_medium_neutral(self) -> None:
        assert is_medium_neutral("CLR") is False

    def test_jurisdiction_wa(self) -> None:
        assert JURISDICTION_FULL_TO_ABBR["Western Australia"] == "WA"

    def test_pinpoint_section(self) -> None:
        assert PINPOINT_CORRECTIONS["Section"] == "s"

    def test_pinpoint_section_sign(self) -> None:
        assert PINPOINT_CORRECTIONS["§"] == "s"

    def test_journal_unswlj(self) -> None:
        assert JOURNAL_ABBREVIATIONS["UNSWLJ"] == "University of New South Wales Law Journal"

    def test_unknown_identifier_returns_none(self) -> None:
        assert get_bracket_type("ZZZZZ") is None

    def test_unknown_not_medium_neutral(self) -> None:
        assert is_medium_neutral("ZZZZZ") is False


class TestAbbreviationsWrapper:
    """Verify abbreviations.py still works with the same interface."""

    def test_clr_bracket_type_enum(self) -> None:
        assert abbr_get_bracket_type("CLR") == BracketType.ROUND

    def test_hca_bracket_type_enum(self) -> None:
        assert abbr_get_bracket_type("HCA") == BracketType.SQUARE

    def test_is_medium_neutral(self) -> None:
        assert abbr_is_medium_neutral("FCA") is True
        assert abbr_is_medium_neutral("CLR") is False

    def test_all_report_series_contains_clr(self) -> None:
        assert "CLR" in ALL_REPORT_SERIES

    def test_all_report_series_contains_hca(self) -> None:
        assert "HCA" in ALL_REPORT_SERIES

    def test_round_bracket_series_has_clr(self) -> None:
        assert "CLR" in ROUND_BRACKET_SERIES

    def test_medium_neutral_has_hca(self) -> None:
        assert "HCA" in MEDIUM_NEUTRAL_IDENTIFIERS

    def test_new_identifiers_present(self) -> None:
        """Verify new court identifiers from reference_data are available."""
        assert "UKSC" in ALL_REPORT_SERIES
        assert "FedCFamC2F" in MEDIUM_NEUTRAL_IDENTIFIERS
        assert "WASAT" in MEDIUM_NEUTRAL_IDENTIFIERS

    def test_backward_compat_extras_in_round(self) -> None:
        """Entries that were in the original hardcoded set but not in reference_data."""
        for abbr in ("TasR", "SR (Qld)", "ICR", "Cr App R", "BCLC", "Lloyd's Rep", "ATPR", "EOC"):
            assert abbr in ROUND_BRACKET_SERIES, f"{abbr} missing from ROUND_BRACKET_SERIES"

    def test_backward_compat_extras_in_medium_neutral(self) -> None:
        """Entries that were in the original hardcoded set but not in COURT_IDENTIFIERS."""
        for abbr in ("FMCA", "NSWCATOD", "NSWCATAP", "QMC", "QCAT", "VCAT", "SACAT", "AAT"):
            assert abbr in MEDIUM_NEUTRAL_IDENTIFIERS, f"{abbr} missing from MEDIUM_NEUTRAL_IDENTIFIERS"

    def test_square_bracket_series_includes_flc(self) -> None:
        assert "FLC" in SQUARE_BRACKET_SERIES

    def test_qdr_variant_in_square(self) -> None:
        """QdR (no space) was in the original hardcoded set."""
        assert "QdR" in SQUARE_BRACKET_SERIES

    def test_unknown_returns_none(self) -> None:
        assert abbr_get_bracket_type("ZZZZZ") is None

    def test_backward_compat_bracket_type_for_extras(self) -> None:
        """Ensure get_bracket_type works for backward-compat-only entries."""
        assert abbr_get_bracket_type("ICR") == BracketType.ROUND
        assert abbr_get_bracket_type("FMCA") == BracketType.SQUARE


class TestJurisdictionsWrapper:
    """Verify jurisdictions.py still works with the same interface."""

    def test_cth_abbreviation(self) -> None:
        assert JURISDICTION_ABBREVIATIONS["Cth"] == "Commonwealth"

    def test_wa_abbreviation(self) -> None:
        assert JURISDICTION_ABBREVIATIONS["WA"] == "Western Australia"

    def test_valid_jurisdictions_set(self) -> None:
        assert "NSW" in VALID_JURISDICTIONS
        assert "Vic" in VALID_JURISDICTIONS
        assert "Qld" in VALID_JURISDICTIONS

    def test_full_name_to_abbreviation(self) -> None:
        assert FULL_NAME_TO_ABBREVIATION["Western Australia"] == "WA"
        assert FULL_NAME_TO_ABBREVIATION["Commonwealth"] == "Cth"

    def test_commonwealth_of_australia_variant(self) -> None:
        assert FULL_NAME_TO_ABBREVIATION["Commonwealth of Australia"] == "Cth"

    def test_section_abbreviations(self) -> None:
        assert SECTION_ABBREVIATIONS["section"] == "s"
        assert SECTION_ABBREVIATIONS["Section"] == "s"
        assert SECTION_ABBREVIATIONS["SECTION"] == "s"
        assert SECTION_ABBREVIATIONS["§"] == "s"

    def test_section_abbreviations_backward_compat(self) -> None:
        """Entries added for backward compat that are not in PINPOINT_CORRECTIONS."""
        assert SECTION_ABBREVIATIONS["Sec"] == "s"
        assert SECTION_ABBREVIATIONS["Sec."] == "s"
        assert SECTION_ABBREVIATIONS["Ch"] == "ch"

    def test_clauses_uses_cll(self) -> None:
        """Original jurisdictions.py used 'cll' for clauses, not 'cls'."""
        assert SECTION_ABBREVIATIONS["clauses"] == "cll"
        assert SECTION_ABBREVIATIONS["Clauses"] == "cll"

    def test_regulation_abbreviation(self) -> None:
        assert SECTION_ABBREVIATIONS["regulation"] == "reg"
        assert SECTION_ABBREVIATIONS["Regulation"] == "reg"


class TestJournalAbbreviationsMerge:
    """Verify journal.py merges reference_data + local extras correctly."""

    def test_entry_from_reference_data(self) -> None:
        from citefix.parsers.journal import JOURNAL_ABBREVIATIONS as j_abbrevs
        assert j_abbrevs["UNSWLJ"] == "University of New South Wales Law Journal"
        assert j_abbrevs["Melb ULR"] == "Melbourne University Law Review"  # reference_data only

    def test_entry_from_local_extras(self) -> None:
        from citefix.parsers.journal import JOURNAL_ABBREVIATIONS as j_abbrevs
        assert j_abbrevs["HLR"] == "Harvard Law Review"  # local extra only
        assert j_abbrevs["YLJ"] == "Yale Law Journal"  # local extra only

    def test_all_original_entries_present(self) -> None:
        """Every abbreviation from the original journal.py must still be present."""
        from citefix.parsers.journal import JOURNAL_ABBREVIATIONS as j_abbrevs
        original_keys = [
            "UNSWLJ", "MULR", "SydLR", "UQLJ", "UWALRev", "UWALR", "AdelLR",
            "ALJ", "AJLL", "AILR", "AIAL Forum", "ALMD", "CLJ", "CJLJ", "FedLR",
            "FedLRev", "JCUL", "LAWASIA J", "LQR", "MLR", "MqLJ", "MonLR",
            "MonULR", "OJLS", "PLPR", "QUT LR", "TPLJ", "UTSLR", "UQLR", "YLJ",
            "HLR", "SLR", "CLR", "GLJ", "AltLJ", "JCULR", "ABLR", "AJHR", "AJLH",
            "AJLP", "AMPLA Bull", "ANU JL", "APLRev", "Austl Bar Rev", "AYBIL",
            "Bond LR", "BondLRev", "CanLR", "CLSR", "CrimLJ", "Deakin LR",
            "DeakinLRev", "EPLJ", "FLJ", "FlindersLJ", "GriffLRev", "ILJ",
            "InsolvLJ", "JBankFinL", "JEqty", "JLIS", "JLM", "LGLJ", "LIJ",
            "MelbJIL", "MJIL", "NTLJ", "NZLR", "NZULRev", "PLR", "PubLR",
            "PropLR", "TasLR", "UNSW LJ", "UTasLR", "UWAL Rev", "VUWLRev",
            "VUWLR", "WALR", "WALRev", "BYIL", "CJQ", "Conv", "Crim LR",
            "CrimLR", "EHRLR", "ELR", "Fam Law", "JLSS", "LS", "NLJ", "NILQ",
            "PL", "SJ", "Stat LR", "CalLR", "CornellLRev", "DukeLJ", "EmoryLJ",
            "FordhamLRev", "IowaLRev", "MichLR", "MinnLR", "NYULR", "NwULR",
            "TexLRev", "TulLRev", "UCLALRev", "UChiLRev", "UPaLRev", "VaLR",
            "VandLRev", "WisLRev", "AJIL", "EJIL", "HarvILJ", "ICLQ", "ILM",
            "JIEL", "LJIL", "YaleJIL",
        ]
        for key in original_keys:
            assert key in j_abbrevs, f"{key} missing from merged JOURNAL_ABBREVIATIONS"

    def test_reference_data_entries_also_present(self) -> None:
        """Entries unique to reference_data must be included via the merge."""
        from citefix.parsers.journal import JOURNAL_ABBREVIATIONS as j_abbrevs
        rd_only_keys = [
            "AILREV", "AIPJ", "AJCL", "AJFL", "APLJ", "AULR", "Adel LR",
            "Alt LJ", "CompLJ", "Crim LJ", "Fed L Rev", "Fed LR", "Griff LR",
            "JAAL", "JCL", "LSWA Brief", "Melb ULR", "Melb Uni L Rev", "Mon LR",
            "Mon ULR", "QUTLR", "Res Judicatae", "SYDLR", "Syd LR", "UTAS LR",
        ]
        for key in rd_only_keys:
            assert key in j_abbrevs, f"{key} from reference_data missing in merged dict"
