"""Tests for the optional AI fallback module.

All tests run WITHOUT an API key -- they either exercise the disabled path or
mock the API client so no real network calls are made.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from citefix.engine.ai_fallback import (
    AIFallback,
    _json_to_parse_result,
    _parse_response_json,
    _runs_to_annotated_text,
)
from citefix.models import FootnoteRun, ParseResult, SourceType


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_runs(text: str, italic: bool = False) -> list[FootnoteRun]:
    return [FootnoteRun(text=text, italic=italic)]


def _make_mixed_runs() -> list[FootnoteRun]:
    """Create runs for: *Mabo v Queensland* (1992) 175 CLR 1."""
    return [
        FootnoteRun(text="Mabo v Queensland", italic=True),
        FootnoteRun(text=" (1992) 175 CLR 1.", italic=False),
    ]


def _mock_api_response(payload: Any) -> MagicMock:
    """Build a mock ``messages.create`` return value."""
    content_block = MagicMock()
    content_block.text = json.dumps(payload) if not isinstance(payload, str) else payload
    response = MagicMock()
    response.content = [content_block]
    return response


# ---------------------------------------------------------------------------
# Tests: helper functions
# ---------------------------------------------------------------------------


class TestRunsToAnnotatedText:
    def test_plain_text(self) -> None:
        runs = [FootnoteRun(text="hello world")]
        assert _runs_to_annotated_text(runs) == "hello world"

    def test_italic_wrapped(self) -> None:
        runs = [FootnoteRun(text="Mabo v Queensland", italic=True)]
        assert _runs_to_annotated_text(runs) == "*Mabo v Queensland*"

    def test_bold_wrapped(self) -> None:
        runs = [FootnoteRun(text="Important", bold=True)]
        assert _runs_to_annotated_text(runs) == "**Important**"

    def test_mixed_runs(self) -> None:
        runs = _make_mixed_runs()
        result = _runs_to_annotated_text(runs)
        assert result == "*Mabo v Queensland* (1992) 175 CLR 1."


class TestParseResponseJson:
    def test_clean_json(self) -> None:
        raw = '{"source_type": "case", "confidence": 0.95, "fields": {}}'
        result = _parse_response_json(raw)
        assert result["source_type"] == "case"
        assert result["confidence"] == 0.95

    def test_json_with_code_fence(self) -> None:
        raw = '```json\n{"source_type": "legislation", "confidence": 0.8, "fields": {}}\n```'
        result = _parse_response_json(raw)
        assert result["source_type"] == "legislation"

    def test_json_with_plain_fence(self) -> None:
        raw = '```\n{"source_type": "book"}\n```'
        result = _parse_response_json(raw)
        assert result["source_type"] == "book"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_response_json("this is not json")

    def test_array_json(self) -> None:
        raw = '[{"source_type": "case"}, {"source_type": "book"}]'
        result = _parse_response_json(raw)
        assert isinstance(result, list)
        assert len(result) == 2


class TestJsonToParseResult:
    def test_valid_case(self) -> None:
        data = {
            "source_type": "case",
            "confidence": 0.95,
            "fields": {"parties": "Mabo v Queensland", "year": "1992"},
        }
        result = _json_to_parse_result(data)
        assert result.source_type == SourceType.CASE
        assert result.confidence == 0.95
        assert result.fields["parties"] == "Mabo v Queensland"

    def test_valid_legislation(self) -> None:
        data = {
            "source_type": "legislation",
            "confidence": 0.88,
            "fields": {"title": "Corporations Act", "year": "2001"},
        }
        result = _json_to_parse_result(data)
        assert result.source_type == SourceType.LEGISLATION
        assert result.confidence == 0.88

    def test_unknown_source_type(self) -> None:
        data = {"source_type": "foobar", "confidence": 0.5, "fields": {}}
        result = _json_to_parse_result(data)
        assert result.source_type == SourceType.UNKNOWN

    def test_missing_fields_key(self) -> None:
        data = {"source_type": "case", "confidence": 0.9}
        result = _json_to_parse_result(data)
        assert result.fields == {}

    def test_non_dict_fields_becomes_empty(self) -> None:
        data = {"source_type": "case", "confidence": 0.9, "fields": "bad"}
        result = _json_to_parse_result(data)
        assert result.fields == {}

    def test_confidence_clamped_high(self) -> None:
        data = {"source_type": "case", "confidence": 5.0, "fields": {}}
        result = _json_to_parse_result(data)
        assert result.confidence == 1.0

    def test_confidence_clamped_low(self) -> None:
        data = {"source_type": "case", "confidence": -1.0, "fields": {}}
        result = _json_to_parse_result(data)
        assert result.confidence == 0.0

    def test_missing_confidence_defaults_zero(self) -> None:
        data = {"source_type": "case", "fields": {}}
        result = _json_to_parse_result(data)
        assert result.confidence == 0.0

    def test_all_source_types(self) -> None:
        for label in (
            "case", "legislation", "journal_article", "book",
            "chapter", "report", "website", "treaty", "hansard",
        ):
            data = {"source_type": label, "confidence": 0.8, "fields": {}}
            result = _json_to_parse_result(data)
            assert result.source_type != SourceType.UNKNOWN, f"{label} mapped to UNKNOWN"


# ---------------------------------------------------------------------------
# Tests: AIFallback with no API key (disabled path)
# ---------------------------------------------------------------------------


class TestAIFallbackDisabled:
    """Verify graceful degradation when no API key or anthropic package."""

    def test_not_available_without_key(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            fb = AIFallback()
            assert fb.is_available is False

    def test_classify_returns_unknown_when_disabled(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            fb = AIFallback()
            result = fb.classify("Some text.", _make_runs("Some text."))
            assert result.source_type == SourceType.UNKNOWN
            assert result.confidence == 0.0

    def test_batch_classify_returns_unknowns_when_disabled(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            fb = AIFallback()
            items = [
                ("Mabo v Queensland (1992) 175 CLR 1.", _make_runs("Mabo")),
                ("Corporations Act 2001 (Cth) s 180.", _make_runs("Corp")),
            ]
            results = fb.batch_classify(items)
            assert len(results) == 2
            assert all(r.source_type == SourceType.UNKNOWN for r in results)

    def test_batch_classify_empty_list(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            fb = AIFallback()
            assert fb.batch_classify([]) == []

    def test_import_error_disables_fallback(self) -> None:
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"}),
            patch.dict("sys.modules", {"anthropic": None}),
        ):
            fb = AIFallback()
            assert fb.is_available is False


# ---------------------------------------------------------------------------
# Tests: AIFallback with mocked client (simulates API calls)
# ---------------------------------------------------------------------------


class TestAIFallbackWithMock:
    """Test the classify / batch_classify logic with a mocked Anthropic client."""

    def _make_fallback(self) -> AIFallback:
        """Create an AIFallback with a mock client injected."""
        with patch.dict("os.environ", {}, clear=True):
            fb = AIFallback()
        # Bypass normal init -- inject a mock client directly
        fb._client = MagicMock()
        fb._last_request_time = 0.0
        return fb

    # -- classify ------------------------------------------------------------

    def test_classify_case(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            {
                "source_type": "case",
                "confidence": 0.95,
                "fields": {
                    "parties": "Mabo v Queensland (No 2)",
                    "year": "1992",
                    "volume": "175",
                    "report_series": "CLR",
                    "start_page": "1",
                    "pinpoint": "42",
                },
            }
        )

        result = fb.classify(
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
            _make_mixed_runs(),
        )

        assert result.source_type == SourceType.CASE
        assert result.confidence == 0.95
        assert result.fields["parties"] == "Mabo v Queensland (No 2)"
        assert result.fields["year"] == "1992"

    def test_classify_legislation(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            {
                "source_type": "legislation",
                "confidence": 0.92,
                "fields": {
                    "title": "Corporations Act",
                    "year": "2001",
                    "jurisdiction": "Cth",
                    "pinpoint_type": "s",
                    "pinpoint": "180(1)",
                },
            }
        )

        runs = [
            FootnoteRun(text="Corporations Act 2001", italic=True),
            FootnoteRun(text=" (Cth) s 180(1)."),
        ]
        result = fb.classify("Corporations Act 2001 (Cth) s 180(1).", runs)

        assert result.source_type == SourceType.LEGISLATION
        assert result.confidence == 0.92
        assert result.fields["jurisdiction"] == "Cth"

    def test_classify_journal_article(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            {
                "source_type": "journal_article",
                "confidence": 0.88,
                "fields": {
                    "author": "Jani McCutcheon",
                    "title": "The Vanishing Author",
                    "year": "2013",
                    "volume": "36",
                    "journal": "University of New South Wales Law Journal",
                    "start_page": "915",
                },
            }
        )

        text = (
            "Jani McCutcheon, 'The Vanishing Author' (2013) 36 "
            "University of New South Wales Law Journal 915."
        )
        result = fb.classify(text, _make_runs(text))
        assert result.source_type == SourceType.JOURNAL_ARTICLE
        assert result.fields["author"] == "Jani McCutcheon"

    def test_classify_handles_code_fence_response(self) -> None:
        fb = self._make_fallback()
        fenced = '```json\n{"source_type": "book", "confidence": 0.85, "fields": {"title": "Authority to Decide"}}\n```'
        fb._client.messages.create.return_value = _mock_api_response(fenced)

        result = fb.classify("Mark Leeming, Authority to Decide...", _make_runs("text"))
        assert result.source_type == SourceType.BOOK

    def test_classify_handles_api_exception(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.side_effect = RuntimeError("network error")

        result = fb.classify("Some citation.", _make_runs("Some citation."))
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0

    def test_classify_handles_bad_json(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            "I'm sorry, I can't parse that citation."
        )

        result = fb.classify("Garbled text.", _make_runs("Garbled text."))
        assert result.source_type == SourceType.UNKNOWN
        assert result.confidence == 0.0

    def test_classify_uses_prompt_caching(self) -> None:
        """Verify the system prompt includes cache_control for prompt caching."""
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            {"source_type": "case", "confidence": 0.9, "fields": {}}
        )

        fb.classify("Some text.", _make_runs("Some text."))

        call_kwargs = fb._client.messages.create.call_args
        system_arg = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system")
        assert isinstance(system_arg, list)
        assert len(system_arg) == 1
        assert system_arg[0]["cache_control"] == {"type": "ephemeral"}

    def test_classify_uses_correct_model(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            {"source_type": "case", "confidence": 0.9, "fields": {}}
        )

        fb.classify("Some text.", _make_runs("Some text."))

        call_kwargs = fb._client.messages.create.call_args
        model_arg = call_kwargs.kwargs.get("model") or call_kwargs[1].get("model")
        assert model_arg == "claude-sonnet-4-6"

    # -- batch_classify ------------------------------------------------------

    def test_batch_classify_success(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            [
                {
                    "source_type": "case",
                    "confidence": 0.9,
                    "fields": {"parties": "Mabo v Queensland"},
                },
                {
                    "source_type": "legislation",
                    "confidence": 0.85,
                    "fields": {"title": "Corporations Act"},
                },
            ]
        )

        items = [
            ("Mabo v Queensland (1992) 175 CLR 1.", _make_mixed_runs()),
            ("Corporations Act 2001 (Cth) s 180.", _make_runs("Corp Act")),
        ]
        results = fb.batch_classify(items)

        assert len(results) == 2
        assert results[0].source_type == SourceType.CASE
        assert results[1].source_type == SourceType.LEGISLATION

    def test_batch_classify_empty_list_skips_api(self) -> None:
        fb = self._make_fallback()
        results = fb.batch_classify([])
        assert results == []
        fb._client.messages.create.assert_not_called()

    def test_batch_classify_handles_api_exception(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.side_effect = RuntimeError("timeout")

        items = [
            ("Citation 1.", _make_runs("c1")),
            ("Citation 2.", _make_runs("c2")),
        ]
        results = fb.batch_classify(items)

        assert len(results) == 2
        assert all(r.source_type == SourceType.UNKNOWN for r in results)

    def test_batch_classify_handles_non_array_response(self) -> None:
        fb = self._make_fallback()
        # API returns a single object instead of an array
        fb._client.messages.create.return_value = _mock_api_response(
            {"source_type": "case", "confidence": 0.9, "fields": {}}
        )

        items = [("Citation.", _make_runs("c"))]
        results = fb.batch_classify(items)

        assert len(results) == 1
        assert results[0].source_type == SourceType.UNKNOWN

    def test_batch_classify_pads_short_response(self) -> None:
        fb = self._make_fallback()
        # API returns fewer results than items sent
        fb._client.messages.create.return_value = _mock_api_response(
            [{"source_type": "case", "confidence": 0.9, "fields": {}}]
        )

        items = [
            ("Citation 1.", _make_runs("c1")),
            ("Citation 2.", _make_runs("c2")),
            ("Citation 3.", _make_runs("c3")),
        ]
        results = fb.batch_classify(items)

        assert len(results) == 3
        assert results[0].source_type == SourceType.CASE
        assert results[1].source_type == SourceType.UNKNOWN
        assert results[2].source_type == SourceType.UNKNOWN

    def test_batch_classify_trims_long_response(self) -> None:
        fb = self._make_fallback()
        # API returns more results than items sent
        fb._client.messages.create.return_value = _mock_api_response(
            [
                {"source_type": "case", "confidence": 0.9, "fields": {}},
                {"source_type": "book", "confidence": 0.8, "fields": {}},
                {"source_type": "treaty", "confidence": 0.7, "fields": {}},
            ]
        )

        items = [("Citation 1.", _make_runs("c1"))]
        results = fb.batch_classify(items)

        assert len(results) == 1
        assert results[0].source_type == SourceType.CASE

    def test_batch_classify_handles_bad_entries_in_array(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            [
                {"source_type": "case", "confidence": 0.9, "fields": {}},
                "not a dict",  # bad entry
                42,  # also bad
            ]
        )

        items = [
            ("Citation 1.", _make_runs("c1")),
            ("Citation 2.", _make_runs("c2")),
            ("Citation 3.", _make_runs("c3")),
        ]
        results = fb.batch_classify(items)

        assert len(results) == 3
        assert results[0].source_type == SourceType.CASE
        assert results[1].source_type == SourceType.UNKNOWN
        assert results[2].source_type == SourceType.UNKNOWN

    def test_batch_classify_handles_bad_json(self) -> None:
        fb = self._make_fallback()
        fb._client.messages.create.return_value = _mock_api_response(
            "Sorry, I cannot classify these."
        )

        items = [("Citation.", _make_runs("c"))]
        results = fb.batch_classify(items)

        assert len(results) == 1
        assert results[0].source_type == SourceType.UNKNOWN


# ---------------------------------------------------------------------------
# Tests: should_use_ai standalone function
# ---------------------------------------------------------------------------


class TestShouldUseAI:
    """Test the should_use_ai() heuristic."""

    def test_low_confidence(self) -> None:
        from citefix.engine.ai_fallback import should_use_ai
        assert should_use_ai(0.3, [], "some text") is True

    def test_high_confidence(self) -> None:
        from citefix.engine.ai_fallback import should_use_ai
        assert should_use_ai(0.95, [], "some text") is False

    def test_wrong_style_supra(self) -> None:
        from citefix.engine.ai_fallback import should_use_ai
        assert should_use_ai(0.8, [], "Mabo, supra note 1, at 42") is True

    def test_wrong_style_id(self) -> None:
        from citefix.engine.ai_fallback import should_use_ai
        assert should_use_ai(0.8, [], "Id. at 55") is True

    def test_many_unfixable_issues(self) -> None:
        from citefix.engine.ai_fallback import should_use_ai

        class FakeIssue:
            def __init__(self, fixable: bool) -> None:
                self.auto_fixable = fixable

        issues = [FakeIssue(False), FakeIssue(False), FakeIssue(False)]
        assert should_use_ai(0.9, issues, "text") is True

    def test_few_unfixable_issues(self) -> None:
        from citefix.engine.ai_fallback import should_use_ai

        class FakeIssue:
            def __init__(self, fixable: bool) -> None:
                self.auto_fixable = fixable

        issues = [FakeIssue(False), FakeIssue(True)]
        assert should_use_ai(0.9, issues, "text") is False
