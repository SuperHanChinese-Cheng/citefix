"""Journal article citation parser (AGLC4 Rule 5.1)."""

from __future__ import annotations

import regex

from citefix.models import FootnoteRun, ParseResult, SourceType
from citefix.parsers.base import BaseCitationParser
from citefix.rules.reference_data import JOURNAL_ABBREVIATIONS as _RD_JOURNAL_ABBREVS

# Merge: reference_data is base, local extras override/supplement
JOURNAL_ABBREVIATIONS: dict[str, str] = dict(_RD_JOURNAL_ABBREVS)
JOURNAL_ABBREVIATIONS.update({
    # --- Extras not in reference_data ---
    "UWALRev": "University of Western Australia Law Review",
    "AdelLR": "Adelaide Law Review",
    "AILR": "Australian Indigenous Law Review",
    "AIAL Forum": "AIAL Forum",
    "CJLJ": "Canadian Journal of Law and Jurisprudence",
    "FedLRev": "Federal Law Review",
    "JCUL": "James Cook University Law Review",
    "LAWASIA J": "LAWASIA Journal",
    "MqLJ": "Macquarie Law Journal",
    "MonLR": "Monash University Law Review",
    "MonULR": "Monash University Law Review",
    "PLPR": "Property Law and Practice Review",
    "TPLJ": "Torts Law Journal",
    "UTSLR": "University of Technology Sydney Law Review",
    "UQLR": "University of Queensland Law Review",
    "YLJ": "Yale Law Journal",
    "HLR": "Harvard Law Review",
    "SLR": "Stanford Law Review",
    "CLR": "Columbia Law Review",
    "GLJ": "Georgetown Law Journal",
    "AltLJ": "Alternative Law Journal",
    # --- Australian ---
    "AJHR": "Australian Journal of Human Rights",
    "AJLH": "Australian Journal of Legal History",
    "AJLP": "Australian Journal of Legal Philosophy",
    "AMPLA Bull": "AMPLA Bulletin",
    "ANU JL": "Australian National University Journal of Law",
    "APLRev": "Asia Pacific Law Review",
    "Austl Bar Rev": "Australian Bar Review",
    "AYBIL": "Australian Year Book of International Law",
    "Bond LR": "Bond Law Review",
    "BondLRev": "Bond Law Review",
    "CanLR": "Canberra Law Review",
    "CLSR": "Computer Law and Security Review",
    "CrimLJ": "Criminal Law Journal",
    "DeakinLRev": "Deakin Law Review",
    "FLJ": "Flinders Law Journal",
    "FlindersLJ": "Flinders Law Journal",
    "GriffLRev": "Griffith Law Review",
    "ILJ": "Industrial Law Journal",
    "InsolvLJ": "Insolvency Law Journal",
    "JBankFinL": "Journal of Banking and Finance Law",
    "JEqty": "Journal of Equity",
    "JLIS": "Journal of Law and Information Science",
    "JLM": "Journal of Law and Medicine",
    "LGLJ": "Local Government Law Journal",
    "LIJ": "Law Institute Journal",
    "MelbJIL": "Melbourne Journal of International Law",
    "MJIL": "Melbourne Journal of International Law",
    "NTLJ": "Northern Territory Law Journal",
    "NZLR": "New Zealand Law Review",
    "NZULRev": "New Zealand Universities Law Review",
    "PubLR": "Public Law Review",
    "PropLR": "Property Law Review",
    "TasLR": "Tasmania Law Review",
    "UTasLR": "University of Tasmania Law Review",
    "UWAL Rev": "University of Western Australia Law Review",
    "VUWLRev": "Victoria University of Wellington Law Review",
    "VUWLR": "Victoria University of Wellington Law Review",
    "WALR": "Western Australian Law Review",
    "WALRev": "Western Australian Law Review",
    # --- UK ---
    "BYIL": "British Year Book of International Law",
    "CJQ": "Civil Justice Quarterly",
    "Conv": "Conveyancer and Property Lawyer",
    "Crim LR": "Criminal Law Review",
    "CrimLR": "Criminal Law Review",
    "EHRLR": "European Human Rights Law Review",
    "ELR": "Edinburgh Law Review",
    "Fam Law": "Family Law",
    "JLSS": "Journal of the Law Society of Scotland",
    "LS": "Legal Studies",
    "NLJ": "New Law Journal",
    "NILQ": "Northern Ireland Legal Quarterly",
    "PL": "Public Law",
    "SJ": "Solicitors Journal",
    "Stat LR": "Statute Law Review",
    # --- US ---
    "CalLR": "California Law Review",
    "CornellLRev": "Cornell Law Review",
    "DukeLJ": "Duke Law Journal",
    "EmoryLJ": "Emory Law Journal",
    "FordhamLRev": "Fordham Law Review",
    "IowaLRev": "Iowa Law Review",
    "MichLR": "Michigan Law Review",
    "MinnLR": "Minnesota Law Review",
    "NYULR": "New York University Law Review",
    "NwULR": "Northwestern University Law Review",
    "TexLRev": "Texas Law Review",
    "TulLRev": "Tulane Law Review",
    "UCLALRev": "UCLA Law Review",
    "UChiLRev": "University of Chicago Law Review",
    "UPaLRev": "University of Pennsylvania Law Review",
    "VaLR": "Virginia Law Review",
    "VandLRev": "Vanderbilt Law Review",
    "WisLRev": "Wisconsin Law Review",
    # --- International ---
    "AJIL": "American Journal of International Law",
    "EJIL": "European Journal of International Law",
    "HarvILJ": "Harvard International Law Journal",
    "ICLQ": "International and Comparative Law Quarterly",
    "ILM": "International Legal Materials",
    "JIEL": "Journal of International Economic Law",
    "LJIL": "Leiden Journal of International Law",
    "YaleJIL": "Yale Journal of International Law",
})

_KNOWN_ABBREVIATIONS: set[str] = set(JOURNAL_ABBREVIATIONS.keys())

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Character class matching any quote character (single, double, smart)
_Q = r"""['\"'‘’“”]"""

SURNAME_FIRST_PATTERN = regex.compile(
    r"^(?P<surname>[\p{Lu}][\p{L}'''-]+)"
    r",\s+"
    r"(?P<given>[\p{Lu}][\p{L}'''-]+"
    r"(?:\s+[\p{Lu}][\p{L}'''-]*)*"
    r")"
    r"(?=\s*,\s*" + _Q + r")",
    regex.UNICODE,
)

JOURNAL_ARTICLE_PATTERN = regex.compile(
    r"(?P<author>.+?)"
    r",\s*"
    r"(?P<open_quote>" + _Q + r")"
    r"(?P<title>.+?)"
    r"(?P<close_quote>" + _Q + r")"
    r"\s*"
    r"(?:\[(?P<year_sq>\d{4})\]|\((?P<year_rd>\d{4})\))"
    r"\s+"
    r"(?P<volume>\d+)"
    r"(?:\((?P<issue>[^)]+)\))?"
    r"\s+"
    r"(?P<journal_name>.+?)"
    r"\s+"
    r"(?P<start_page>\d+(?:\s*[-–]\s*\d+)?)"  # Allow page ranges: "70-95" or "70–95"
    r"(?:"
    r"\s*,\s*"
    r"(?:at\s+)?"
    r"(?:p\.?\s*|pp\.?\s*|page\s+)?"
    r"(?P<pinpoint>"
    r"\d+"
    r"(?:\s*[-–]\s*\d+)?"
    r")"
    r")?"
    r"\s*\.?\s*$",
    regex.UNICODE,
)

JOURNAL_SIGNAL_PATTERN = regex.compile(
    _Q
    + r".+?"
    + _Q
    + r"\s*"
    r"(?:\[\d{4}\]|\(\d{4}\))"
    r"\s+"
    r"\d+"
    r"(?:\([^)]+\))?"
    r"\s+"
    r".+?"
    r"\s+"
    r"\d+",
    regex.UNICODE,
)

AT_P_PATTERN = regex.compile(
    r"(?:at\s+)?(?:pp?\.?\s+)\d+",
    regex.UNICODE,
)


class JournalArticleParser(BaseCitationParser):
    """Parses journal article citations per AGLC4 Rule 5.1."""

    def can_parse(self, text: str) -> float:
        text = text.strip().rstrip(".")

        if JOURNAL_ARTICLE_PATTERN.search(text):
            return 0.95

        if JOURNAL_SIGNAL_PATTERN.search(text):
            return 0.7

        return 0.0

    def parse(self, text: str, runs: list[FootnoteRun]) -> ParseResult:
        text_clean = text.strip()

        m = JOURNAL_ARTICLE_PATTERN.search(text_clean)
        if m:
            return self._parse_structured(m, text_clean, runs)

        if JOURNAL_SIGNAL_PATTERN.search(text_clean):
            return ParseResult(
                source_type=SourceType.JOURNAL_ARTICLE,
                confidence=0.5,
                fields={
                    "raw_text": text_clean,
                    "parse_error": "could not fully parse journal article citation",
                },
            )

        return ParseResult(source_type=SourceType.UNKNOWN, confidence=0.0)

    def _parse_structured(
        self,
        m: regex.Match,  # type: ignore[type-arg]
        full_text: str,
        runs: list[FootnoteRun],
    ) -> ParseResult:
        author = m.group("author").strip()
        open_quote = m.group("open_quote")
        close_quote = m.group("close_quote")
        title = m.group("title").strip()
        year = m.group("year_rd") or m.group("year_sq")
        year_bracket = "round" if m.group("year_rd") else "square"
        volume = m.group("volume")
        issue = m.group("issue")
        journal_name = m.group("journal_name").strip()
        start_page = m.group("start_page")
        pinpoint = m.group("pinpoint")

        if pinpoint:
            pinpoint = pinpoint.strip()

        double_quote_chars = {'"', "“", "”"}
        has_double_quotes = open_quote in double_quote_chars or close_quote in double_quote_chars

        has_surname_first = self._detect_surname_first(author)
        has_abbreviated_journal = self._detect_abbreviated_journal(journal_name)
        has_at_p_pinpoint = bool(AT_P_PATTERN.search(full_text))
        has_trailing_dot = full_text.rstrip().endswith(".")
        journal_is_italic = self._check_journal_italic(journal_name, runs)

        has_pinpoint_hyphen = False
        if pinpoint and "-" in pinpoint and "–" not in pinpoint:
            has_pinpoint_hyphen = True

        # Rule 4.1.1: detect initials with periods (e.g. "H.L.A." should be "HLA")
        has_initial_periods = bool(regex.search(r"\b[A-Z]\.", author))

        # Rule 5.5: detect "the" at start of journal name
        has_the_prefix = bool(regex.match(r"^[Tt]he\s+", journal_name))

        return ParseResult(
            source_type=SourceType.JOURNAL_ARTICLE,
            confidence=0.95,
            fields={
                "author": author,
                "title": title,
                "year": year,
                "year_bracket": year_bracket,
                "volume": volume,
                "issue": issue,
                "journal_name": journal_name,
                "start_page": start_page,
                "pinpoint": pinpoint,
                "open_quote": open_quote,
                "close_quote": close_quote,
                "has_double_quotes": has_double_quotes,
                "has_surname_first": has_surname_first,
                "has_abbreviated_journal": has_abbreviated_journal,
                "has_at_p_pinpoint": has_at_p_pinpoint,
                "has_trailing_dot": has_trailing_dot,
                "journal_is_italic": journal_is_italic,
                "has_pinpoint_hyphen": has_pinpoint_hyphen,
                "has_initial_periods": has_initial_periods,
                "has_the_prefix": has_the_prefix,
            },
        )

    def _detect_surname_first(self, author: str) -> bool:
        """Detect if any author is in 'Surname, Given' format."""
        parts = regex.split(r"\s+and\s+", author)
        for part in parts:
            part = part.strip()
            if regex.match(
                r"^[\p{Lu}][\p{L}'''-]+,\s+[\p{Lu}][\p{L}'''-]+",
                part,
                regex.UNICODE,
            ):
                return True
        return False

    def _detect_abbreviated_journal(self, journal_name: str) -> bool:
        """Check if the journal name appears to be abbreviated."""
        cleaned = journal_name.strip()

        if cleaned in _KNOWN_ABBREVIATIONS:
            return True

        words = cleaned.split()
        if len(words) <= 4 and all(
            regex.match(r"^[\p{Lu}]+$", w, regex.UNICODE) for w in words
        ):
            return True

        return False

    def _check_journal_italic(self, journal_name: str, runs: list[FootnoteRun]) -> bool:
        """Check if the journal name text is contained within an italic run."""
        for run in runs:
            if run.italic and journal_name in run.text:
                return True
        return False
