"""Step 1: Extract footnotes from .docx XML."""

from __future__ import annotations

import logging
import zipfile
from io import BytesIO
from pathlib import Path

from lxml import etree

from citefix.text_utils import normalize_text
from citefix.models import Footnote, FootnoteRun

logger = logging.getLogger(__name__)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": W_NS}


def _is_italic(rpr: etree._Element | None) -> bool:
    """Check if a run properties element indicates italic formatting."""
    if rpr is None:
        return False
    italic = rpr.find(f"{{{W_NS}}}i")
    if italic is None:
        return False
    val = italic.get(f"{{{W_NS}}}val")
    return val is None or val.lower() in ("true", "1", "on")


def _is_bold(rpr: etree._Element | None) -> bool:
    """Check if a run properties element indicates bold formatting."""
    if rpr is None:
        return False
    bold = rpr.find(f"{{{W_NS}}}b")
    if bold is None:
        return False
    val = bold.get(f"{{{W_NS}}}val")
    return val is None or val.lower() in ("true", "1", "on")


def _extract_runs(paragraph: etree._Element) -> list[FootnoteRun]:
    """Extract formatted runs from a footnote paragraph element."""
    runs: list[FootnoteRun] = []
    for r_elem in paragraph.findall(f"{{{W_NS}}}r"):
        rpr = r_elem.find(f"{{{W_NS}}}rPr")

        # Skip footnote reference markers (the superscript number)
        if rpr is not None:
            rstyle = rpr.find(f"{{{W_NS}}}rStyle")
            if rstyle is not None and rstyle.get(f"{{{W_NS}}}val") == "FootnoteReference":
                continue

        text_parts: list[str] = []
        for child in r_elem:
            tag = etree.QName(child).localname
            if tag == "t":
                text_parts.append(child.text or "")
            elif tag == "tab":
                text_parts.append("\t")
            elif tag == "br":
                text_parts.append("\n")

        text = "".join(text_parts)
        if not text:
            continue

        runs.append(FootnoteRun(
            text=text,
            italic=_is_italic(rpr),
            bold=_is_bold(rpr),
        ))
    return runs


def extract_footnotes(docx_input: bytes | Path) -> list[Footnote]:
    """Extract all footnotes from a .docx file.

    Args:
        docx_input: Raw .docx bytes or path to a .docx file.

    Returns:
        List of Footnote objects, ordered by footnote index.
        Excludes the two default Word footnotes (separator and continuation).
    """
    if isinstance(docx_input, Path):
        docx_bytes = docx_input.read_bytes()
    else:
        docx_bytes = docx_input

    try:
        zf = zipfile.ZipFile(BytesIO(docx_bytes))
    except zipfile.BadZipFile:
        raise ValueError("Input is not a valid .docx file")

    if "word/footnotes.xml" not in zf.namelist():
        logger.info("No footnotes.xml found in .docx — document has no footnotes")
        return []

    footnotes_xml = zf.read("word/footnotes.xml")
    root = etree.fromstring(footnotes_xml)

    footnotes: list[Footnote] = []
    for fn_elem in root.findall(f"{{{W_NS}}}footnote"):
        fn_type = fn_elem.get(f"{{{W_NS}}}type")
        if fn_type in ("separator", "continuationSeparator"):
            continue

        fn_id_str = fn_elem.get(f"{{{W_NS}}}id")
        if fn_id_str is None:
            continue
        fn_id = int(fn_id_str)
        if fn_id < 1:
            continue

        all_runs: list[FootnoteRun] = []
        for para in fn_elem.findall(f"{{{W_NS}}}p"):
            all_runs.extend(_extract_runs(para))

        if not all_runs:
            continue

        footnotes.append(Footnote(
            index=fn_id,
            runs=all_runs,
            xml_element=fn_elem,
        ))

    footnotes.sort(key=lambda fn: fn.index)

    # Apply Unicode normalization to each footnote's derived plain_text.
    # Run texts stay as-is (needed for XML matching during rewriting).
    # We store the normalized text in the Footnote's __dict__ so that
    # downstream code can access it if needed; the primary normalization
    # also happens in the classifier and parsers before pattern matching.
    for fn in footnotes:
        plain_text = "".join(run.text for run in fn.runs).strip()
        fn.__dict__["_normalized_plain_text"] = normalize_text(plain_text)

    logger.info("Extracted %d footnotes", len(footnotes))
    return footnotes
