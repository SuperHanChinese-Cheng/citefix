"""Tests for cross-reference checker (Ibid and subsequent references)."""

from __future__ import annotations

from citefix.models import ParseResult, SourceType
from citefix.rules.cross_ref import check_cross_references
from tests.conftest import make_footnote


class TestIbidDetection:
    def test_consecutive_same_source_should_be_ibid(self) -> None:
        fn1 = make_footnote(1, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.")
        fn2 = make_footnote(2, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 55.")

        parse_results = {
            1: ParseResult(source_type=SourceType.CASE, confidence=0.9),
            2: ParseResult(source_type=SourceType.CASE, confidence=0.9),
        }

        issues = check_cross_references([fn1, fn2], parse_results)
        assert any(i.rule == "1.4.1" for i in issues)
        ibid_issue = next(i for i in issues if i.rule == "1.4.1")
        assert "Ibid 55" in ibid_issue.suggested

    def test_consecutive_same_source_same_pinpoint_plain_ibid(self) -> None:
        fn1 = make_footnote(1, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.")
        fn2 = make_footnote(2, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.")

        parse_results = {
            1: ParseResult(source_type=SourceType.CASE, confidence=0.9),
            2: ParseResult(source_type=SourceType.CASE, confidence=0.9),
        }

        issues = check_cross_references([fn1, fn2], parse_results)
        ibid_issue = next(i for i in issues if i.rule == "1.4.1")
        assert ibid_issue.suggested == "Ibid."

    def test_non_consecutive_not_ibid(self) -> None:
        fn1 = make_footnote(1, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.")
        fn2 = make_footnote(2, "Palmer v Ayres [2017] HCA 5.")
        fn3 = make_footnote(3, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.")

        parse_results = {
            1: ParseResult(source_type=SourceType.CASE, confidence=0.9),
            2: ParseResult(source_type=SourceType.CASE, confidence=0.9),
            3: ParseResult(source_type=SourceType.CASE, confidence=0.9),
        }

        issues = check_cross_references([fn1, fn2, fn3], parse_results)
        assert not any(i.rule == "1.4.1" and i.footnote_index == 3 for i in issues)

    def test_non_consecutive_suggests_subsequent_ref(self) -> None:
        fn1 = make_footnote(1, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.")
        fn2 = make_footnote(2, "Palmer v Ayres [2017] HCA 5.")
        fn3 = make_footnote(3, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 55.")

        parse_results = {
            1: ParseResult(source_type=SourceType.CASE, confidence=0.9),
            2: ParseResult(source_type=SourceType.CASE, confidence=0.9),
            3: ParseResult(source_type=SourceType.CASE, confidence=0.9),
        }

        issues = check_cross_references([fn1, fn2, fn3], parse_results)
        subseq = [i for i in issues if i.rule == "1.4.2" and i.footnote_index == 3]
        assert len(subseq) == 1
        assert "(n 1)" in subseq[0].suggested


class TestExistingIbid:
    def test_ibid_in_first_footnote_is_error(self) -> None:
        fn1 = make_footnote(1, "Ibid.")

        parse_results = {
            1: ParseResult(source_type=SourceType.IBID, confidence=1.0),
        }

        issues = check_cross_references([fn1], parse_results)
        assert any(i.rule == "1.4.1" and "first footnote" in i.description for i in issues)

    def test_single_footnote_no_issues(self) -> None:
        fn1 = make_footnote(1, "Mabo v Queensland (1992) 175 CLR 1.")

        parse_results = {
            1: ParseResult(source_type=SourceType.CASE, confidence=0.9),
        }

        issues = check_cross_references([fn1], parse_results)
        assert len(issues) == 0
