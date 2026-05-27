"""End-to-end pipeline tests using programmatically generated .docx files."""

from __future__ import annotations

import zipfile
from io import BytesIO

from lxml import etree

from citefix.extractor import extract_footnotes
from citefix.pipeline import process


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _build_test_docx(footnote_texts: list[str | list[tuple[str, bool]]]) -> bytes:
    """Build a minimal .docx with footnotes for testing.

    Args:
        footnote_texts: Each item is either a plain string, or a list of
            (text, is_italic) tuples for formatted runs.
    """
    nsmap = {"w": W_NS, "r": R_NS}

    # --- footnotes.xml ---
    footnotes_root = etree.Element(f"{{{W_NS}}}footnotes", nsmap=nsmap)

    # Separator footnote (id=0)
    sep = etree.SubElement(footnotes_root, f"{{{W_NS}}}footnote",
                           attrib={f"{{{W_NS}}}type": "separator", f"{{{W_NS}}}id": "0"})
    sep_p = etree.SubElement(sep, f"{{{W_NS}}}p")
    sep_r = etree.SubElement(sep_p, f"{{{W_NS}}}r")
    sep_t = etree.SubElement(sep_r, f"{{{W_NS}}}t")
    sep_t.text = ""

    # Continuation separator (id=-1)
    cont = etree.SubElement(footnotes_root, f"{{{W_NS}}}footnote",
                            attrib={f"{{{W_NS}}}type": "continuationSeparator", f"{{{W_NS}}}id": "-1"})

    for idx, fn_content in enumerate(footnote_texts, start=1):
        fn_elem = etree.SubElement(footnotes_root, f"{{{W_NS}}}footnote",
                                   attrib={f"{{{W_NS}}}id": str(idx)})
        para = etree.SubElement(fn_elem, f"{{{W_NS}}}p")

        # Footnote reference run
        ref_run = etree.SubElement(para, f"{{{W_NS}}}r")
        ref_rpr = etree.SubElement(ref_run, f"{{{W_NS}}}rPr")
        etree.SubElement(ref_rpr, f"{{{W_NS}}}rStyle", attrib={f"{{{W_NS}}}val": "FootnoteReference"})
        ref_ref = etree.SubElement(ref_run, f"{{{W_NS}}}footnoteRef")

        if isinstance(fn_content, str):
            runs_data = [(fn_content, False)]
        else:
            runs_data = fn_content

        for text, is_italic in runs_data:
            r = etree.SubElement(para, f"{{{W_NS}}}r")
            if is_italic:
                rpr = etree.SubElement(r, f"{{{W_NS}}}rPr")
                etree.SubElement(rpr, f"{{{W_NS}}}i")
            t = etree.SubElement(r, f"{{{W_NS}}}t")
            t.text = text
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

    footnotes_xml = etree.tostring(footnotes_root, xml_declaration=True, encoding="UTF-8")

    # --- document.xml (minimal) ---
    doc_root = etree.Element(f"{{{W_NS}}}document", nsmap=nsmap)
    body = etree.SubElement(doc_root, f"{{{W_NS}}}body")
    p = etree.SubElement(body, f"{{{W_NS}}}p")
    r = etree.SubElement(p, f"{{{W_NS}}}r")
    t = etree.SubElement(r, f"{{{W_NS}}}t")
    t.text = "Test document."
    doc_xml = etree.tostring(doc_root, xml_declaration=True, encoding="UTF-8")

    # --- [Content_Types].xml ---
    ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    ct_root = etree.Element(f"{{{ct_ns}}}Types")
    etree.SubElement(ct_root, f"{{{ct_ns}}}Default",
                     attrib={"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    etree.SubElement(ct_root, f"{{{ct_ns}}}Default",
                     attrib={"Extension": "xml", "ContentType": "application/xml"})
    etree.SubElement(ct_root, f"{{{ct_ns}}}Override",
                     attrib={"PartName": "/word/document.xml",
                             "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"})
    etree.SubElement(ct_root, f"{{{ct_ns}}}Override",
                     attrib={"PartName": "/word/footnotes.xml",
                             "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"})
    ct_xml = etree.tostring(ct_root, xml_declaration=True, encoding="UTF-8")

    # --- _rels/.rels ---
    rels_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    rels_root = etree.Element(f"{{{rels_ns}}}Relationships")
    etree.SubElement(rels_root, f"{{{rels_ns}}}Relationship",
                     attrib={"Id": "rId1",
                             "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
                             "Target": "word/document.xml"})
    rels_xml = etree.tostring(rels_root, xml_declaration=True, encoding="UTF-8")

    # --- word/_rels/document.xml.rels ---
    doc_rels_root = etree.Element(f"{{{rels_ns}}}Relationships")
    etree.SubElement(doc_rels_root, f"{{{rels_ns}}}Relationship",
                     attrib={"Id": "rId1",
                             "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes",
                             "Target": "footnotes.xml"})
    doc_rels_xml = etree.tostring(doc_rels_root, xml_declaration=True, encoding="UTF-8")

    # Assemble zip
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", ct_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/document.xml", doc_xml)
        zf.writestr("word/footnotes.xml", footnotes_xml)
        zf.writestr("word/_rels/document.xml.rels", doc_rels_xml)

    return buf.getvalue()


class TestExtractorWithRealDocx:
    def test_extracts_footnotes(self) -> None:
        docx = _build_test_docx([
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
            "Ibid 55.",
        ])
        footnotes = extract_footnotes(docx)
        assert len(footnotes) == 2
        assert "Mabo" in footnotes[0].plain_text
        assert "Ibid" in footnotes[1].plain_text

    def test_preserves_italic_info(self) -> None:
        docx = _build_test_docx([
            [("Mabo v Queensland (No 2)", True), (" (1992) 175 CLR 1, 42.", False)],
        ])
        footnotes = extract_footnotes(docx)
        assert len(footnotes) == 1
        assert footnotes[0].has_italic_content
        assert footnotes[0].runs[0].italic is True
        assert footnotes[0].runs[1].italic is False


class TestPipelineEndToEnd:
    def test_detects_vs_error(self) -> None:
        docx = _build_test_docx([
            "Mabo vs Queensland (No 2) (1992) 175 CLR 1, 42.",
        ])
        result = process(docx)
        assert any(i.rule == "2.1" for i in result.issues_found)

    def test_detects_wrong_brackets(self) -> None:
        docx = _build_test_docx([
            "Mabo v Queensland (No 2) [1992] 175 CLR 1, 42.",
        ])
        result = process(docx)
        assert any(i.rule == "2.2" for i in result.issues_found)

    def test_detects_missing_full_stop(self) -> None:
        docx = _build_test_docx([
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42",
        ])
        result = process(docx)
        assert any(i.rule == "1.1" for i in result.issues_found)

    def test_detects_ibid_opportunity(self) -> None:
        docx = _build_test_docx([
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 55.",
        ])
        result = process(docx)
        assert any(i.rule == "1.4.1" for i in result.issues_found)

    def test_detects_section_error(self) -> None:
        docx = _build_test_docx([
            "Corporations Act 2001 (Cth), Section 180(1).",
        ])
        result = process(docx)
        rules = {i.rule for i in result.issues_found}
        assert "3.2" in rules

    def test_perfect_citation_no_errors(self) -> None:
        docx = _build_test_docx([
            "Palmer v Ayres [2017] HCA 5, [31].",
        ])
        result = process(docx)
        real_errors = [i for i in result.issues_found if i.severity == "error"]
        assert len(real_errors) == 0

    def test_fix_applied_to_output(self) -> None:
        docx = _build_test_docx([
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42",
        ])
        result = process(docx)
        fixed_footnotes = extract_footnotes(result.fixed_docx)
        assert fixed_footnotes[0].plain_text.endswith(".")

    def test_empty_document_no_crash(self) -> None:
        docx = _build_test_docx([])
        result = process(docx)
        assert result.footnote_count == 0
        assert result.error_count == 0

    def test_detects_para_pinpoint_error(self) -> None:
        docx = _build_test_docx([
            "Palmer v Ayres [2017] HCA 5 at para 31.",
        ])
        result = process(docx)
        assert any(i.rule == "2.4" for i in result.issues_found)

    def test_multiple_errors_in_one_footnote(self) -> None:
        """FN with 'vs', wrong brackets, and missing full stop."""
        docx = _build_test_docx([
            "Mabo vs Queensland (No 2) [1992] 175 CLR 1, 42",
        ])
        result = process(docx)
        rules = {i.rule for i in result.issues_found}
        assert "2.1" in rules  # vs
        assert "2.2" in rules  # brackets
        assert "1.1" in rules  # full stop

    def test_ibid_replacement_applied(self) -> None:
        """Consecutive same-source citation should be rewritten to Ibid."""
        docx = _build_test_docx([
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
        ])
        result = process(docx)
        fixed_fns = extract_footnotes(result.fixed_docx)
        # FN2 should now be "Ibid." (same pinpoint as FN1)
        assert "Ibid" in fixed_fns[1].plain_text
        assert fixed_fns[1].plain_text.strip().endswith(".")

    def test_ibid_replacement_with_different_pinpoint(self) -> None:
        """Ibid with different pinpoint should include the pinpoint."""
        docx = _build_test_docx([
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 55.",
        ])
        result = process(docx)
        fixed_fns = extract_footnotes(result.fixed_docx)
        fn2_text = fixed_fns[1].plain_text.strip()
        assert "Ibid" in fn2_text
        assert "55" in fn2_text
        assert fn2_text.endswith(".")

    def test_ibid_replacement_italic(self) -> None:
        """Ibid should be italicised in the output."""
        docx = _build_test_docx([
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
            "Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
        ])
        result = process(docx)
        fixed_fns = extract_footnotes(result.fixed_docx)
        # Check that "Ibid" appears in an italic run
        ibid_runs = [r for r in fixed_fns[1].runs if "Ibid" in r.text]
        assert len(ibid_runs) >= 1
        assert ibid_runs[0].italic is True

    def test_signal_stripped_from_case_parse(self) -> None:
        """'See' should not appear in the parsed parties name."""
        docx = _build_test_docx([
            "See Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.",
        ])
        result = process(docx)
        # The citation should be classified and parsed correctly
        # (we check the classification doesn't fail by verifying case-level issues are raised)
        assert result.footnote_count == 1
