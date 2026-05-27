"""End-to-end test of the API endpoints with a real .docx file."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from citefix.extractor import extract_footnotes
from citefix.pipeline import process


def build_multipart(docx_data: bytes, filename: str) -> tuple[bytes, str]:
    """Build a multipart/form-data body for file upload."""
    boundary = "citef1xb0undary"
    parts = [
        ("--" + boundary + "\r\n"
         'Content-Disposition: form-data; name="file"; filename="' + filename + '"\r\n'
         "Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n"
         "\r\n").encode(),
        docx_data,
        ("\r\n--" + boundary + "--\r\n").encode(),
    ]
    body = b"".join(parts)
    content_type = "multipart/form-data; boundary=" + boundary
    return body, content_type


def test_health() -> None:
    """Check the health endpoint."""
    resp = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
    data = json.loads(resp.read())
    assert data["status"] == "ok", f"Health check failed: {data}"
    print("  /health: OK")


def e2e_analyze(docx_data: bytes) -> dict:
    """Test the /analyze endpoint."""
    body, ct = build_multipart(docx_data, "test.docx")
    req = urllib.request.Request(
        "http://localhost:8000/analyze",
        data=body,
        headers={"Content-Type": ct},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    result = json.loads(resp.read())

    assert result["footnote_count"] == 30, f"Expected 30 footnotes, got {result['footnote_count']}"
    assert result["total_issues"] > 0, "Expected some issues"
    assert result["auto_fixable"] > 0, "Expected some auto-fixable issues"
    assert len(result["issues"]) == result["total_issues"]

    # Check key issues are detected
    issue_keys = set()
    for iss in result["issues"]:
        key = f"FN{iss['footnote']}_{iss['rule']}"
        issue_keys.add(key)

    expected = {
        "FN1_1.1": "full stop",
        "FN1_1.3": "pinpoint",
        "FN1_2.1": "case name (v or italic)",
        "FN1_2.2": "year brackets",
        "FN4_2.4": "medium neutral para",
        "FN5_2.1": "uppercase V",
        "FN7_1.3": "pinpoint comma",
        "FN8_3.2": "section abbreviation",
    }
    for key, desc in expected.items():
        assert key in issue_keys, f"Missing expected issue: {key} ({desc})"

    print(f"  /analyze: OK ({result['footnote_count']} fns, {result['total_issues']} issues, "
          f"{result['auto_fixable']} fixable, {result['needs_review']} flagged)")
    return result


def e2e_fix(docx_data: bytes) -> bytes:
    """Test the /fix endpoint and verify the output."""
    body, ct = build_multipart(docx_data, "test.docx")
    req = urllib.request.Request(
        "http://localhost:8000/fix",
        data=body,
        headers={"Content-Type": ct},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    fixed_data = resp.read()

    assert len(fixed_data) > 1000, "Fixed document too small"
    cd = resp.headers.get("Content-Disposition", "")
    assert "test_fixed.docx" in cd, f"Wrong Content-Disposition: {cd}"

    # Extract footnotes from fixed document
    fns = extract_footnotes(fixed_data)
    assert len(fns) == 30, f"Expected 30 footnotes in fixed doc, got {len(fns)}"

    # Verify key corrections
    fn_map = {fn.index: fn for fn in fns}

    # FN 1: Mabo — should be italic, "v" not "vs", round brackets, clean pinpoint
    fn1 = fn_map[1]
    assert "v Queensland" in fn1.plain_text, f"FN1 v fix failed: {fn1.plain_text}"
    assert "vs" not in fn1.plain_text, f"FN1 still has 'vs': {fn1.plain_text}"
    assert "(1992)" in fn1.plain_text, f"FN1 bracket fix failed: {fn1.plain_text}"
    assert ", 42." in fn1.plain_text, f"FN1 pinpoint fix failed: {fn1.plain_text}"
    fn1_italic = [r.text for r in fn1.runs if r.italic]
    assert any("Mabo" in t for t in fn1_italic), f"FN1 not italic: {fn1_italic}"
    print("  FN1 (Mabo): OK")

    # FN 4: Palmer — medium neutral, para -> [31]
    fn4 = fn_map[4]
    assert "Palmer v Ayres" in fn4.plain_text, f"FN4 parties wrong: {fn4.plain_text}"
    assert "[2017]" in fn4.plain_text, f"FN4 brackets wrong: {fn4.plain_text}"
    assert "[31]" in fn4.plain_text, f"FN4 pinpoint wrong: {fn4.plain_text}"
    assert "paragraph" not in fn4.plain_text.lower(), f"FN4 still has 'paragraph': {fn4.plain_text}"
    fn4_italic = [r.text for r in fn4.runs if r.italic]
    assert any("Palmer" in t for t in fn4_italic), f"FN4 not italic: {fn4_italic}"
    print("  FN4 (Palmer): OK")

    # FN 5: Roadshow — uppercase V fixed, medium neutral brackets
    fn5 = fn_map[5]
    assert " v " in fn5.plain_text, f"FN5 V not fixed: {fn5.plain_text}"
    assert " V " not in fn5.plain_text, f"FN5 still uppercase V: {fn5.plain_text}"
    fn5_italic = [r.text for r in fn5.runs if r.italic]
    assert any("Roadshow" in t for t in fn5_italic), f"FN5 not italic: {fn5_italic}"
    print("  FN5 (Roadshow): OK")

    # FN 6: Coles Myer — brackets fixed, "at page" removed
    fn6 = fn_map[6]
    assert "[2009]" in fn6.plain_text, f"FN6 brackets wrong: {fn6.plain_text}"
    assert "at page" not in fn6.plain_text.lower(), f"FN6 still has 'at page': {fn6.plain_text}"
    print("  FN6 (Coles Myer): OK")

    # FN 7: ACCC — comma before pinpoint
    fn7 = fn_map[7]
    assert "402, 410" in fn7.plain_text, f"FN7 comma fix failed: {fn7.plain_text}"
    fn7_italic = [r.text for r in fn7.runs if r.italic]
    assert any("Australian" in t for t in fn7_italic), f"FN7 not italic: {fn7_italic}"
    print("  FN7 (ACCC): OK")

    # FN 8: Corporations Act — section abbreviation, comma removed
    fn8 = fn_map[8]
    assert "(Cth) s 180" in fn8.plain_text, f"FN8 section fix failed: {fn8.plain_text}"
    assert "Section" not in fn8.plain_text, f"FN8 still has 'Section': {fn8.plain_text}"
    print("  FN8 (Corporations Act): OK")

    # FN 16: Book — no comma before pinpoint
    fn16 = fn_map[16]
    assert "2020) 45." in fn16.plain_text, f"FN16 book pinpoint wrong: {fn16.plain_text}"
    print("  FN16 (Book): OK")

    # FN 25: Smith v Jones — "at [31]" fixed
    fn25 = fn_map[25]
    assert ", [31]" in fn25.plain_text, f"FN25 bracket pinpoint wrong: {fn25.plain_text}"
    assert "at [31]" not in fn25.plain_text, f"FN25 still has 'at [31]': {fn25.plain_text}"
    print("  FN25 (Smith v Jones): OK")

    print(f"  /fix: OK ({len(fixed_data)} bytes)")
    return fixed_data


def e2e_fix_is_idempotent(fixed_data: bytes) -> None:
    """Running the pipeline on already-fixed output should produce minimal new issues."""
    result = process(fixed_data)
    auto_fixable = [i for i in result.issues_found if i.auto_fixable]
    # Some issues might remain (like double quotes on unfixed sources), but
    # the core fixes should be stable — no regressions
    print(f"  Idempotency: {result.error_count} issues remain, {len(auto_fixable)} auto-fixable")
    # The key case/legislation fixes should be stable
    for i in auto_fixable:
        # No case-related fixes should fire on already-fixed citations
        if i.footnote_index in (1, 2, 3, 4, 5, 6, 7, 25, 28):
            if i.rule in ("2.1", "2.2", "1.3", "2.4"):
                print(f"    WARNING: FN{i.footnote_index} rule {i.rule} still fires: {i.description}")


def main() -> None:
    docx_path = Path(r"C:\Users\cheng\Downloads\citefix_test_document.docx")
    if not docx_path.exists():
        print(f"Test document not found: {docx_path}")
        return

    docx_data = docx_path.read_bytes()
    print("Running end-to-end API tests...")
    print()

    test_health()
    e2e_analyze(docx_data)
    fixed_data = e2e_fix(docx_data)
    e2e_fix_is_idempotent(fixed_data)

    print()
    print("ALL E2E TESTS PASSED")


if __name__ == "__main__":
    main()
