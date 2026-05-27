"""Tests for the citation classifier."""

from __future__ import annotations

from citefix.classifier import Classifier
from citefix.models import SourceType
from citefix.parsers.ibid import IbidParser, SubsequentRefParser
from tests.conftest import make_footnote


class TestClassifier:
    def setup_method(self) -> None:
        self.classifier = Classifier()

    def test_classify_case_reported(self) -> None:
        fn = make_footnote(1, "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.")
        source_type, confidence, parser = self.classifier.classify(fn)
        assert source_type == SourceType.CASE
        assert confidence >= 0.9

    def test_classify_case_medium_neutral(self) -> None:
        fn = make_footnote(1, "Palmer v Ayres [2017] HCA 5, [31].")
        source_type, confidence, parser = self.classifier.classify(fn)
        assert source_type == SourceType.CASE
        assert confidence >= 0.8

    def test_classify_legislation(self) -> None:
        fn = make_footnote(1, "Corporations Act 2001 (Cth) s 180(1).")
        source_type, confidence, parser = self.classifier.classify(fn)
        assert source_type == SourceType.LEGISLATION
        assert confidence >= 0.9

    def test_classify_ibid(self) -> None:
        fn = make_footnote(1, "Ibid.")
        source_type, confidence, _ = self.classifier.classify(fn)
        assert source_type == SourceType.IBID
        assert confidence == 1.0

    def test_classify_ibid_with_pinpoint(self) -> None:
        fn = make_footnote(1, "Ibid 55.")
        source_type, confidence, _ = self.classifier.classify(fn)
        assert source_type == SourceType.IBID
        assert confidence == 1.0

    def test_classify_ibid_lowercase(self) -> None:
        fn = make_footnote(1, "ibid")
        source_type, confidence, _ = self.classifier.classify(fn)
        assert source_type == SourceType.IBID

    def test_classify_subsequent_ref(self) -> None:
        fn = make_footnote(1, "Mabo (n 3) 55.")
        source_type, confidence, _ = self.classifier.classify(fn)
        assert source_type == SourceType.SUBSEQUENT_REF
        assert confidence >= 0.8

    def test_classify_unknown(self) -> None:
        fn = make_footnote(1, "This is just some random text.")
        source_type, confidence, _ = self.classifier.classify(fn)
        assert source_type == SourceType.UNKNOWN
        assert confidence < 0.3

    def test_ibid_returns_parser(self) -> None:
        """Quick-path ibid must return IbidParser so pipeline can parse fields."""
        fn = make_footnote(1, "Ibid.")
        source_type, confidence, parser = self.classifier.classify(fn)
        assert source_type == SourceType.IBID
        assert parser is not None
        assert isinstance(parser, IbidParser)

    def test_ibid_with_pinpoint_returns_parser(self) -> None:
        fn = make_footnote(1, "Ibid 55.")
        _, _, parser = self.classifier.classify(fn)
        assert parser is not None
        assert isinstance(parser, IbidParser)

    def test_subsequent_ref_returns_parser(self) -> None:
        """Quick-path subsequent ref must return SubsequentRefParser."""
        fn = make_footnote(1, "Mabo (n 3) 55.")
        source_type, _, parser = self.classifier.classify(fn)
        assert source_type == SourceType.SUBSEQUENT_REF
        assert parser is not None
        assert isinstance(parser, SubsequentRefParser)

    def test_see_case_classified_correctly(self) -> None:
        """Signal-prefixed case citation should still classify as CASE."""
        fn = make_footnote(1, "See Mabo v Queensland (No 2) (1992) 175 CLR 1.")
        source_type, confidence, parser = self.classifier.classify(fn)
        assert source_type == SourceType.CASE
        assert confidence >= 0.9
        assert parser is not None

    def test_see_also_legislation_classified(self) -> None:
        """Signal-prefixed legislation should still classify as LEGISLATION."""
        fn = make_footnote(1, "See also Corporations Act 2001 (Cth) s 180(1).")
        source_type, confidence, parser = self.classifier.classify(fn)
        assert source_type == SourceType.LEGISLATION
        assert confidence >= 0.9
