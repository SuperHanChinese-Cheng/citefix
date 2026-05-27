"""Step 6: Apply fixes back to .docx footnote XML."""

from __future__ import annotations

import copy
import logging
import zipfile
from io import BytesIO

import regex
from lxml import etree

from citefix.models import Footnote, Issue
from citefix.rules.normalizer import normalize_footnote_text

logger = logging.getLogger(__name__)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"


class Rewriter:
    """Applies citation fixes to .docx footnote XML.

    Makes surgical edits — never rebuilds footnotes from scratch.
    """

    def apply_fixes(
        self,
        docx_bytes: bytes,
        footnotes: list[Footnote],
        issues: list[Issue],
    ) -> bytes:
        """Apply all auto-fixable issues to the .docx and return the modified bytes."""
        fixable = [i for i in issues if i.auto_fixable]
        if not fixable:
            return docx_bytes

        # Bug 5 fix: sort so text substitutions run before italic/formatting fixes.
        # Italic fixes search for text that may have been changed by prior text fixes,
        # so text fixes must come first.
        def _italic_last(issue: Issue) -> int:
            return 1 if "italic" in issue.description.lower() else 0

        fixable = sorted(fixable, key=_italic_last)

        issues_by_fn: dict[int, list[Issue]] = {}
        for issue in fixable:
            issues_by_fn.setdefault(issue.footnote_index, []).append(issue)

        zf_in = zipfile.ZipFile(BytesIO(docx_bytes))
        footnotes_xml = zf_in.read("word/footnotes.xml")
        root = etree.fromstring(footnotes_xml)

        self._normalized_fns: set[int] = set()

        for fn_elem in root.findall(f"{{{W_NS}}}footnote"):
            fn_id_str = fn_elem.get(f"{{{W_NS}}}id")
            if fn_id_str is None:
                continue
            fn_id = int(fn_id_str)

            fn_issues = issues_by_fn.get(fn_id, [])
            if not fn_issues:
                continue

            for issue in fn_issues:
                self._apply_single_fix(fn_elem, issue)

            # Final pass: run character-level normalizer on all text elements
            self._normalize_text_final(fn_elem)

        modified_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

        output = BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.infolist():
                if item.filename == "word/footnotes.xml":
                    zf_out.writestr(item, modified_xml)
                else:
                    zf_out.writestr(item, zf_in.read(item.filename))

        return output.getvalue()

    def _normalize_footnote_xml(self, fn_elem: etree._Element) -> None:
        """Normalize Unicode oddities in all <w:t> elements of a footnote.

        Replaces non-breaking spaces, zero-width characters, fullwidth punctuation,
        and em-dashes so that downstream text searches match reliably.
        Called once per footnote on first encounter.
        """
        _ZERO_WIDTH = "​‌‍﻿"

        for t_elem in self._get_text_elements(fn_elem):
            text = t_elem.text
            if not text:
                continue
            # Non-breaking space → regular space
            text = text.replace("\xa0", " ")
            # Remove zero-width characters
            for ch in _ZERO_WIDTH:
                text = text.replace(ch, "")
            # Fullwidth parentheses → ASCII
            text = text.replace("（", "(")
            text = text.replace("）", ")")
            # Fullwidth comma → ASCII
            text = text.replace("，", ",")
            # Em-dash → en-dash
            text = text.replace("—", "–")
            t_elem.text = text

    def _normalize_text_final(self, fn_elem: etree._Element) -> None:
        """Run character-level normalizer on each <w:t> element after all fixes.

        This is the ABSOLUTE LAST step — handles spacing, punctuation, dashes,
        quotes, and full-stop enforcement on individual text runs.
        We only apply a subset of the normalizer per-run (not full-stop logic,
        which is footnote-level) to avoid breaking cross-run text.
        """
        t_elems = self._get_text_elements(fn_elem)
        if not t_elems:
            return

        for t_elem in t_elems:
            text = t_elem.text
            if not text:
                continue
            # Remove zero-width characters
            text = regex.sub(r"[​‌‍﻿]", "", text)
            # Non-breaking space → regular space
            text = text.replace("\xa0", " ")
            # Fullwidth brackets
            text = text.replace("（", "(").replace("）", ")")
            text = text.replace("［", "[").replace("］", "]")
            # Collapse double spaces
            text = regex.sub(r" {2,}", " ", text)
            # Hyphen/em-dash between digits → en-dash
            text = regex.sub(r"(\d)\s*[-—]\s*(\d)", r"\1–\2", text)
            # Section spacing: "s14" → "s 14"
            text = regex.sub(
                r"\b(s|ss|reg|regs|r|rr|cl|cls|pt|pts|div|divs|sch|schs)(\d)",
                r"\1 \2",
                text,
            )
            if text != t_elem.text:
                t_elem.text = text
                # Preserve whitespace
                if " " in text:
                    t_elem.set(f"{{{XML_NS}}}space", "preserve")

    def _apply_single_fix(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Apply a single fix to a footnote XML element."""
        # Normalize footnote XML once on first encounter (Bug 1 + Bug 3 fix)
        fn_id_str = fn_elem.get(f"{{{W_NS}}}id")
        fn_id = int(fn_id_str) if fn_id_str is not None else id(fn_elem)
        if fn_id not in self._normalized_fns:
            self._normalized_fns.add(fn_id)
            self._normalize_footnote_xml(fn_elem)

        match issue.rule:
            case "1.1":
                self._fix_full_stop(fn_elem)
            case "1.3" if "en-dash" in issue.description:
                self._fix_en_dash(fn_elem, issue)
            case "1.3" if "vol" in issue.description.lower():
                self._fix_text_replace(fn_elem, issue)
            case "1.3":
                self._fix_pinpoint(fn_elem, issue)
            case "1.4.1" if "should use ibid" in issue.description.lower():
                self._fix_ibid_replacement(fn_elem, issue)
            case "1.4.2" if "supra" in issue.description.lower():
                self._fix_subsequent_reference(fn_elem, issue)
            case "1.4.2" if "above n" in issue.description.lower():
                self._fix_subsequent_reference(fn_elem, issue)
            case "1.4.2" if "(note" in issue.description.lower():
                self._fix_subsequent_reference(fn_elem, issue)
            case "1.4.2":
                self._fix_subsequent_reference(fn_elem, issue)
            case "1.4.1" if "not 'id.'" in issue.description.lower():
                self._fix_ibid_replacement(fn_elem, issue)
            case "1.4.1" if "comma" in issue.description.lower():
                self._fix_ibid_comma(fn_elem)
            case "1.4.1" if "italicised" in issue.description.lower():
                self._fix_ibid_italics(fn_elem)
            case "1.4.1" if "capitalised" in issue.description.lower():
                self._fix_ibid_capitalisation(fn_elem)
            case "2.1" if "period" in issue.description.lower() and "no" in issue.description.lower():
                self._fix_text_replace(fn_elem, issue)
            case "2.1" if "comma before year" in issue.description.lower():
                self._fix_text_replace(fn_elem, issue)
            case "2.1" if "not be in quotes" in issue.description.lower() and "case" in issue.description.lower():
                self._fix_case_name_quotes(fn_elem, issue)
            case "2.1" if "italic" in issue.description.lower():
                self._fix_case_name_italics(fn_elem, issue)
            case "2.1":
                self._fix_v_separator(fn_elem, issue)
            case "2.2" if "periods" in issue.description.lower() and "report" in issue.description.lower():
                self._fix_text_replace(fn_elem, issue)
            case "2.2" if "duplicate" in issue.description.lower():
                self._fix_text_replace(fn_elem, issue)
            case "2.2":
                self._fix_year_brackets(fn_elem, issue)
            case "1.1.6":
                self._fix_bare_pinpoint_brackets(fn_elem, issue)
            case "2.4":
                self._fix_para_to_brackets(fn_elem, issue)
            case "3.1" if "abbreviated jurisdiction" in issue.description.lower():
                self._fix_jurisdiction_abbreviation(fn_elem, issue)
            case "3.1" if "must be in brackets" in issue.description.lower():
                self._fix_bare_jurisdiction_brackets(fn_elem, issue)
            case "3.1" if "italic" in issue.description.lower():
                self._fix_legislation_italics(fn_elem, issue)
            case "3.1" if "not be italic" in issue.description.lower():
                self._fix_jurisdiction_not_italic(fn_elem, issue)
            case "3.2" if "comma" in issue.description.lower():
                self._fix_comma_before_section(fn_elem)
            case "3.2" if "space required" in issue.description.lower():
                self._fix_section_spacing(fn_elem, issue)
            case "3.2":
                self._fix_section_abbreviation(fn_elem, issue)
            case "5.1" if "surname" in issue.description.lower():
                self._fix_author_name_order(fn_elem, issue)
            case "5.1" if "single quotes" in issue.description.lower():
                self._fix_double_quotes(fn_elem)
            case "5.1" if "full journal name" in issue.description.lower():
                self._fix_journal_abbreviation(fn_elem, issue)
            case "5.1" if "journal" in issue.description.lower() and "italic" in issue.description.lower():
                self._fix_journal_italics(fn_elem, issue)
            case "5.2" if "not be in quotes" in issue.description.lower():
                self._fix_book_title_quotes(fn_elem, issue)
            case "5.2" if "book title" in issue.description.lower() and "italic" in issue.description.lower():
                self._fix_book_title_italics(fn_elem, issue)
            case "5.2" if (
                "ed" in issue.description.lower()
                and "edition" in issue.description.lower()
            ):
                self._fix_edition_abbreviation(fn_elem, issue)
            case "5.2" if "pinpoint" in issue.description.lower():
                self._fix_book_pinpoint_prefix(fn_elem, issue)
            case "4.1" if "and" in issue.description.lower() and "&" in issue.description.lower():
                self._fix_text_replace(fn_elem, issue)
            case "4.1":
                self._fix_initial_periods(fn_elem, issue)
            case "5.5" if "the" in issue.description.lower():
                self._fix_journal_the_prefix(fn_elem, issue)
            case "general":
                self._fix_double_spaces(fn_elem)
            case _:
                logger.debug("No auto-fix handler for rule %s: %s", issue.rule, issue.description)

    def _get_text_elements(self, fn_elem: etree._Element) -> list[etree._Element]:
        """Get all <w:t> elements in a footnote."""
        return fn_elem.findall(f".//{{{W_NS}}}t")

    def _cross_run_text_replace(
        self, fn_elem: etree._Element, old_text: str, new_text: str
    ) -> bool:
        """Replace text that may span multiple XML <w:t> runs.

        Concatenates all run texts, finds old_text in the concatenated string,
        performs the replacement, then redistributes the result back across runs.
        Returns True if a replacement was made.
        """
        t_elems = self._get_text_elements(fn_elem)
        if not t_elems:
            return False

        # Build concatenated text with boundary tracking
        concat = ""
        boundaries: list[tuple[int, int, etree._Element]] = []
        for t_elem in t_elems:
            text = t_elem.text or ""
            start = len(concat)
            concat += text
            boundaries.append((start, len(concat), t_elem))

        idx = concat.find(old_text)
        if idx < 0:
            return False

        end_idx = idx + len(old_text)

        # Identify affected runs (those overlapping the match region)
        affected: list[tuple[int, int, etree._Element]] = []
        for b_start, b_end, t_elem in boundaries:
            if b_end <= idx or b_start >= end_idx:
                continue
            affected.append((b_start, b_end, t_elem))

        if not affected:
            return False

        # Concatenate text from affected runs and do the replacement locally
        first_start = affected[0][0]
        last_end = affected[-1][1]
        affected_text = concat[first_start:last_end]
        local_idx = idx - first_start
        replaced = (
            affected_text[:local_idx]
            + new_text
            + affected_text[local_idx + len(old_text):]
        )

        # Put the full replaced text into the first affected <w:t>
        first_t = affected[0][2]
        first_t.text = replaced
        # Preserve xml:space="preserve" if there are any spaces
        if " " in replaced:
            first_t.set(f"{{{XML_NS}}}space", "preserve")

        # Clear subsequent affected <w:t> elements
        for _, _, t_elem in affected[1:]:
            t_elem.text = ""

        return True

    def _fix_full_stop(self, fn_elem: etree._Element) -> None:
        """Append a full stop to the last text element."""
        t_elems = self._get_text_elements(fn_elem)
        if t_elems:
            last_t = t_elems[-1]
            if last_t.text and not last_t.text.rstrip().endswith("."):
                last_t.text = last_t.text.rstrip() + "."

    def _fix_v_separator(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace 'vs', 'vs.', 'versus', uppercase 'V' with lowercase 'v'."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                # Replace "vs", "vs.", "versus" (any case)
                t_elem.text = regex.sub(
                    r"\b(vs\.?|versus)\b", "v", t_elem.text, flags=regex.IGNORECASE
                )
                # Replace standalone uppercase "V" between spaces
                t_elem.text = regex.sub(r"(?<=\s)V(?=\s)", "v", t_elem.text)

    def _fix_year_brackets(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Fix year bracket type (round <-> square)."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return
        # Fallback: text may span multiple runs
        self._cross_run_text_replace(fn_elem, issue.current, issue.suggested)

    def _fix_en_dash(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace hyphens with en-dashes in page ranges."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return
        self._cross_run_text_replace(fn_elem, issue.current, issue.suggested)

    def _fix_pinpoint(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Remove 'at', 'p.', 'page' from pinpoints."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return
        self._cross_run_text_replace(fn_elem, issue.current, issue.suggested)

    def _fix_comma_before_section(self, fn_elem: etree._Element) -> None:
        """Remove comma between jurisdiction and section pinpoint."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                t_elem.text = regex.sub(r"\)\s*,\s*s\b", ") s", t_elem.text)

    def _fix_section_abbreviation(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace 'section', 'Section', etc with 's'."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return
        self._cross_run_text_replace(fn_elem, issue.current, issue.suggested)

    def _fix_bare_pinpoint_brackets(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Wrap bare number pinpoint in square brackets for medium-neutral citations.

        e.g., "HCA 5, 31" → "HCA 5, [31]"
        Only wraps numbers NOT already inside brackets to avoid [[15]] artifacts.
        """
        bare_num = issue.current  # e.g., "15" or "5-25"
        if not bare_num:
            return
        for t_elem in self._get_text_elements(fn_elem):
            if not t_elem.text or bare_num not in t_elem.text:
                continue
            # Use regex: match the bare number only when NOT preceded by [ or followed by ]
            new_text = regex.sub(
                r"(?<!\[)" + regex.escape(bare_num) + r"(?!\])",
                issue.suggested,
                t_elem.text,
                count=1,
            )
            if new_text != t_elem.text:
                t_elem.text = new_text
                return

    def _fix_para_to_brackets(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace 'para 31' / 'at paragraph 31' / 'at [31]' with ', [31]'."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return
        self._cross_run_text_replace(fn_elem, issue.current, issue.suggested)

    def _fix_double_spaces(self, fn_elem: etree._Element) -> None:
        """Replace double spaces with single spaces."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                while "  " in t_elem.text:
                    t_elem.text = t_elem.text.replace("  ", " ")

    def _fix_case_name_italics(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Add italics to case name by splitting XML runs.

        Finds the parties text in the footnote, splits the containing <w:r>
        into up to 3 new runs: before (non-italic), case name (italic), after (non-italic).
        """
        parties = issue.current
        if not parties:
            return

        # Build search variations: original text and v-normalised version
        search_texts = [parties]
        normalised = regex.sub(r"\s+(vs\.?|versus|V)\s+", " v ", parties, flags=regex.IGNORECASE)
        if normalised != parties:
            search_texts.append(normalised)

        for t_elem in self._get_text_elements(fn_elem):
            text = t_elem.text
            if not text:
                continue

            # Skip the footnote reference run
            r_elem = t_elem.getparent()
            if r_elem is None:
                continue
            if r_elem.find(f"{{{W_NS}}}footnoteRef") is not None:
                continue

            # Check if run is already italic
            rpr = r_elem.find(f"{{{W_NS}}}rPr")
            if rpr is not None and rpr.find(f"{{{W_NS}}}i") is not None:
                continue  # Already italic — skip

            for search in search_texts:
                idx = text.find(search)
                if idx < 0:
                    continue

                p_elem = r_elem.getparent()
                if p_elem is None:
                    continue
                r_index = list(p_elem).index(r_elem)

                before_text = text[:idx]
                case_name = text[idx:idx + len(search)]
                after_text = text[idx + len(search):]

                new_elements: list[etree._Element] = []

                # 1. Before text (non-italic) — preserve original formatting
                if before_text:
                    before_r = self._make_run(before_text, rpr, italic=False)
                    new_elements.append(before_r)

                # 2. Case name (italic)
                italic_r = self._make_run(case_name, rpr, italic=True)
                new_elements.append(italic_r)

                # 3. After text (non-italic)
                if after_text:
                    after_r = self._make_run(after_text, rpr, italic=False)
                    new_elements.append(after_r)

                # Replace original <w:r> with new runs
                for i, new_r in enumerate(new_elements):
                    if i == 0:
                        p_elem.remove(r_elem)
                        p_elem.insert(r_index, new_r)
                    else:
                        p_elem.insert(r_index + i, new_r)

                return  # Done — one case name per footnote

        # Bug 2 fix: cross-run fallback — case name may span multiple XML runs.
        self._fix_case_name_italics_cross_run(fn_elem, search_texts)

    def _fix_case_name_italics_cross_run(
        self,
        fn_elem: etree._Element,
        search_texts: list[str],
    ) -> None:
        """Fallback: find and italicise a case name that spans multiple <w:r> runs."""
        # Collect runs from the first paragraph (excluding footnoteRef runs)
        p_elem = fn_elem.find(f".//{{{W_NS}}}p")
        if p_elem is None:
            return

        runs: list[etree._Element] = []
        for r_elem in p_elem.findall(f"{{{W_NS}}}r"):
            if r_elem.find(f"{{{W_NS}}}footnoteRef") is not None:
                continue
            t_elem = r_elem.find(f"{{{W_NS}}}t")
            if t_elem is not None and t_elem.text:
                runs.append(r_elem)

        if not runs:
            return

        # Build concatenated text with boundary tracking
        concat = ""
        boundaries: list[tuple[int, int, etree._Element]] = []  # (start, end, run_elem)
        for r_elem in runs:
            t_elem = r_elem.find(f"{{{W_NS}}}t")
            t_text = t_elem.text if t_elem is not None and t_elem.text else ""
            start = len(concat)
            concat += t_text
            boundaries.append((start, len(concat), r_elem))

        # Search for the case name in the concatenated text
        for search in search_texts:
            idx = concat.find(search)
            if idx < 0:
                continue
            end_idx = idx + len(search)

            # Determine which runs are affected
            for b_start, b_end, r_elem in boundaries:
                # Skip runs entirely before or after the match
                if b_end <= idx or b_start >= end_idx:
                    continue

                t_elem = r_elem.find(f"{{{W_NS}}}t")
                if t_elem is None:
                    continue
                rpr = r_elem.find(f"{{{W_NS}}}rPr")

                # Check if already italic — leave alone
                if rpr is not None and rpr.find(f"{{{W_NS}}}i") is not None:
                    continue

                # Calculate overlap within this run's text
                run_match_start = max(idx, b_start) - b_start
                run_match_end = min(end_idx, b_end) - b_start
                run_text = t_elem.text or ""

                if run_match_start == 0 and run_match_end == len(run_text):
                    # Entire run is inside the match — just make it italic
                    if rpr is None:
                        rpr = etree.SubElement(r_elem, f"{{{W_NS}}}rPr")
                        r_elem.insert(0, rpr)
                    etree.SubElement(rpr, f"{{{W_NS}}}i")
                    etree.SubElement(rpr, f"{{{W_NS}}}iCs")
                else:
                    # Partial overlap — split the run
                    r_index = list(p_elem).index(r_elem)
                    before_text = run_text[:run_match_start]
                    match_text = run_text[run_match_start:run_match_end]
                    after_text = run_text[run_match_end:]

                    new_elements: list[etree._Element] = []
                    if before_text:
                        new_elements.append(self._make_run(before_text, rpr, italic=False))
                    new_elements.append(self._make_run(match_text, rpr, italic=True))
                    if after_text:
                        new_elements.append(self._make_run(after_text, rpr, italic=False))

                    p_elem.remove(r_elem)
                    for i, new_r in enumerate(new_elements):
                        p_elem.insert(r_index + i, new_r)

            return  # Done after first match

    def _make_run(
        self,
        text: str,
        base_rpr: etree._Element | None,
        italic: bool,
    ) -> etree._Element:
        """Create a new <w:r> element with given text and formatting."""
        r = etree.Element(f"{{{W_NS}}}r")

        # Build <w:rPr> — copy base properties, then set/clear italic
        rpr = etree.SubElement(r, f"{{{W_NS}}}rPr")
        if base_rpr is not None:
            for child in base_rpr:
                tag = etree.QName(child.tag).localname
                if tag not in ("i", "iCs"):
                    rpr.append(copy.deepcopy(child))
        if italic:
            etree.SubElement(rpr, f"{{{W_NS}}}i")
            etree.SubElement(rpr, f"{{{W_NS}}}iCs")

        # Build <w:t>
        t = etree.SubElement(r, f"{{{W_NS}}}t")
        t.text = text
        if text and (text[0] == " " or text[-1] == " "):
            t.set(f"{{{XML_NS}}}space", "preserve")

        return r

    def _fix_legislation_italics(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Add italics to legislation title + year.

        issue.current contains "Title Year" e.g. "Limitation Act 2005".
        Splits the containing <w:r> so that "Title Year" is italic and everything
        else (especially the jurisdiction like "(WA)") stays non-italic.

        Same split-run technique as _fix_case_name_italics.
        """
        title_year = issue.current
        if not title_year:
            return

        for t_elem in self._get_text_elements(fn_elem):
            text = t_elem.text
            if not text:
                continue

            r_elem = t_elem.getparent()
            if r_elem is None:
                continue
            # Skip footnote reference runs
            if r_elem.find(f"{{{W_NS}}}footnoteRef") is not None:
                continue

            # Check if already italic
            rpr = r_elem.find(f"{{{W_NS}}}rPr")
            if rpr is not None and rpr.find(f"{{{W_NS}}}i") is not None:
                continue

            idx = text.find(title_year)
            if idx < 0:
                continue

            p_elem = r_elem.getparent()
            if p_elem is None:
                continue
            r_index = list(p_elem).index(r_elem)

            before_text = text[:idx]
            target = text[idx:idx + len(title_year)]
            after_text = text[idx + len(title_year):]

            new_elements: list[etree._Element] = []

            if before_text:
                new_elements.append(self._make_run(before_text, rpr, italic=False))

            new_elements.append(self._make_run(target, rpr, italic=True))

            if after_text:
                new_elements.append(self._make_run(after_text, rpr, italic=False))

            for i, new_r in enumerate(new_elements):
                if i == 0:
                    p_elem.remove(r_elem)
                    p_elem.insert(r_index, new_r)
                else:
                    p_elem.insert(r_index + i, new_r)

            return  # Done

    def _fix_jurisdiction_not_italic(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Remove italics from jurisdiction abbreviation like (WA), (Cth).

        Same split-run technique but in reverse — splits an italic run to make
        the jurisdiction portion non-italic.
        """
        jurisdiction_text = issue.current  # e.g. "(WA)"
        if not jurisdiction_text:
            return

        for t_elem in self._get_text_elements(fn_elem):
            text = t_elem.text
            if not text:
                continue

            r_elem = t_elem.getparent()
            if r_elem is None:
                continue

            # Only process italic runs
            rpr = r_elem.find(f"{{{W_NS}}}rPr")
            if rpr is None or rpr.find(f"{{{W_NS}}}i") is None:
                continue

            idx = text.find(jurisdiction_text)
            if idx < 0:
                continue

            p_elem = r_elem.getparent()
            if p_elem is None:
                continue
            r_index = list(p_elem).index(r_elem)

            before_text = text[:idx]
            target = text[idx:idx + len(jurisdiction_text)]
            after_text = text[idx + len(jurisdiction_text):]

            new_elements: list[etree._Element] = []

            if before_text:
                new_elements.append(self._make_run(before_text, rpr, italic=True))

            # Jurisdiction: NOT italic
            new_elements.append(self._make_run(target, rpr, italic=False))

            if after_text:
                new_elements.append(self._make_run(after_text, rpr, italic=True))

            for i, new_r in enumerate(new_elements):
                if i == 0:
                    p_elem.remove(r_elem)
                    p_elem.insert(r_index, new_r)
                else:
                    p_elem.insert(r_index + i, new_r)

            return

    def _fix_jurisdiction_abbreviation(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace full jurisdiction name with abbreviation.

        e.g., (Western Australia) → (WA), (Commonwealth) → (Cth)
        """
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return

    def _fix_bare_jurisdiction_brackets(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Wrap bare jurisdiction abbreviation in brackets.

        e.g., "Rules 2015 NSW regulation" → "Rules 2015 (NSW) regulation"
        The issue.current is the bare abbreviation (e.g., "NSW"),
        issue.suggested is the bracketed form (e.g., "(NSW)").
        """
        bare = issue.current  # e.g., "NSW"
        bracketed = issue.suggested  # e.g., "(NSW)"
        if not bare:
            return

        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                # Match the bare abbreviation as a whole word (not inside brackets already)
                # Use word boundary to avoid replacing "NSW" inside "NSWLR" etc.
                new_text = regex.sub(
                    r"(?<!\()\b" + regex.escape(bare) + r"\b(?!\))",
                    bracketed,
                    t_elem.text,
                    count=1,
                )
                if new_text != t_elem.text:
                    t_elem.text = new_text
                    return

    def _fix_double_quotes(self, fn_elem: etree._Element) -> None:
        """Replace double quotes around article/chapter titles with single quotes."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                # Smart double quotes -> smart single quotes
                t_elem.text = t_elem.text.replace("“", "‘")  # noqa: RUF001
                t_elem.text = t_elem.text.replace("”", "’")  # noqa: RUF001
                # Straight double quotes -> single quotes (only around text, not in middle)
                t_elem.text = regex.sub(r'"([^"]+)"', r"'\1'", t_elem.text)

    def _fix_edition_abbreviation(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace 'edition' or 'edn' with 'ed'."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                t_elem.text = regex.sub(r"\bedition\b", "ed", t_elem.text, flags=regex.IGNORECASE)
                t_elem.text = regex.sub(r"\bedn\b", "ed", t_elem.text, flags=regex.IGNORECASE)

    def _fix_book_pinpoint_prefix(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Remove 'p', 'p.', 'page' prefix from book pinpoints."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                # "p 45" or "p. 45" or "page 45" at end of citation
                t_elem.text = regex.sub(
                    r"\b(?:pages?\s+|pp?\.?\s+)(\d+)", r"\1", t_elem.text
                )

    def _fix_ibid_replacement(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace entire footnote content with Ibid (with optional pinpoint).

        Preserves the footnoteRef run and paragraph properties, replaces all
        other content runs with an italic 'Ibid' run (plus non-italic pinpoint
        and full stop if needed).
        """
        # Parse suggested text: "Ibid." or "Ibid 42." or "Ibid [31]."
        suggested = issue.suggested.strip()

        for p_elem in fn_elem.findall(f"{{{W_NS}}}p"):
            # Collect runs to keep (footnoteRef) and runs to remove (content)
            ref_runs: list[etree._Element] = []
            content_runs: list[etree._Element] = []

            for child in list(p_elem):
                tag = etree.QName(child.tag).localname
                if tag == "pPr":
                    continue  # Always keep paragraph properties
                if tag == "r":
                    if child.find(f"{{{W_NS}}}footnoteRef") is not None:
                        ref_runs.append(child)
                    else:
                        content_runs.append(child)
                elif tag in ("hyperlink", "ins", "del"):
                    content_runs.append(child)

            if not content_runs:
                continue  # No content to replace in this paragraph

            # Remove all content runs
            for r in content_runs:
                p_elem.remove(r)

            # Determine insert position (after footnoteRef runs)
            if ref_runs:
                insert_after = list(p_elem).index(ref_runs[-1]) + 1
            else:
                # After pPr if present, else at start
                ppr = p_elem.find(f"{{{W_NS}}}pPr")
                insert_after = (list(p_elem).index(ppr) + 1) if ppr is not None else 0

            # Build the replacement: " Ibid[ pinpoint]."
            # Leading space separates from the footnote reference number
            ibid_run = self._make_run(" Ibid", None, italic=True)
            p_elem.insert(insert_after, ibid_run)
            insert_after += 1

            # Extract pinpoint from suggested text (everything after "Ibid" except trailing ".")
            after_ibid = suggested[4:].rstrip(".")  # strip "Ibid" prefix and trailing "."
            if after_ibid:
                pin_text = after_ibid + "."
                pin_run = self._make_run(pin_text, None, italic=False)
                p_elem.insert(insert_after, pin_run)
            else:
                # No pinpoint — add just the full stop to the ibid run
                ibid_t = ibid_run.find(f"{{{W_NS}}}t")
                if ibid_t is not None and ibid_t.text:
                    ibid_t.text += "."

            return  # Only process the first content paragraph

    def _fix_ibid_comma(self, fn_elem: etree._Element) -> None:
        """Remove comma after Ibid before pinpoint."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                t_elem.text = regex.sub(r'\b(Ibid|ibid),\s+', r'\1 ', t_elem.text)

    def _fix_ibid_italics(self, fn_elem: etree._Element) -> None:
        """Make 'Ibid' italic."""
        for t_elem in self._get_text_elements(fn_elem):
            text = t_elem.text
            if not text:
                continue

            m = regex.search(r'\b[Ii]bid\b', text)
            if not m:
                continue

            r_elem = t_elem.getparent()
            if r_elem is None:
                continue

            # Check if already italic
            rpr = r_elem.find(f"{{{W_NS}}}rPr")
            if rpr is not None and rpr.find(f"{{{W_NS}}}i") is not None:
                continue

            p_elem = r_elem.getparent()
            if p_elem is None:
                continue
            r_index = list(p_elem).index(r_elem)

            before_text = text[:m.start()]
            ibid_text = text[m.start():m.end()]
            after_text = text[m.end():]

            new_elements = []
            if before_text:
                new_elements.append(self._make_run(before_text, rpr, italic=False))
            new_elements.append(self._make_run(ibid_text, rpr, italic=True))
            if after_text:
                new_elements.append(self._make_run(after_text, rpr, italic=False))

            for i, new_r in enumerate(new_elements):
                if i == 0:
                    p_elem.remove(r_elem)
                    p_elem.insert(r_index, new_r)
                else:
                    p_elem.insert(r_index + i, new_r)
            return

    def _fix_section_spacing(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Add space between section abbreviation and number.

        Handles the case where a prior abbreviation fix (e.g., § → s) has already
        modified the text, so the original issue.current no longer matches.
        Falls back to regex-based matching of any abbreviation glued to a digit.
        """
        for t_elem in self._get_text_elements(fn_elem):
            if not t_elem.text:
                continue
            # Try direct replacement first
            if issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return
            # Fallback: regex match for abbreviation stuck to digit (post-abbreviation-fix)
            new_text = regex.sub(
                r"\b(s|ss|reg|regs|cl|cll|pt|div|sch|para|r|rr)(\d)",
                r"\1 \2",
                t_elem.text,
                count=1,
            )
            if new_text != t_elem.text:
                t_elem.text = new_text
                return

    def _fix_ibid_capitalisation(self, fn_elem: etree._Element) -> None:
        """Capitalise 'ibid' to 'Ibid'."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                t_elem.text = regex.sub(r"\bibid\b", "Ibid", t_elem.text, flags=regex.IGNORECASE)

    def _fix_subsequent_reference(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace full citation with subsequent reference format.

        Replaces entire footnote content with: Short title (n X) pinpoint.
        Same technique as _fix_ibid_replacement — preserves footnoteRef run.
        """
        suggested = issue.suggested.strip()

        for p_elem in fn_elem.findall(f"{{{W_NS}}}p"):
            ref_runs: list[etree._Element] = []
            content_runs: list[etree._Element] = []

            for child in list(p_elem):
                tag = etree.QName(child.tag).localname
                if tag == "pPr":
                    continue
                if tag == "r":
                    if child.find(f"{{{W_NS}}}footnoteRef") is not None:
                        ref_runs.append(child)
                    else:
                        content_runs.append(child)
                elif tag in ("hyperlink", "ins", "del"):
                    content_runs.append(child)

            if not content_runs:
                continue

            for r in content_runs:
                p_elem.remove(r)

            if ref_runs:
                insert_after = list(p_elem).index(ref_runs[-1]) + 1
            else:
                ppr = p_elem.find(f"{{{W_NS}}}pPr")
                insert_after = (list(p_elem).index(ppr) + 1) if ppr is not None else 0

            # Build: " Short title (n X) pinpoint."
            content_run = self._make_run(f" {suggested}", None, italic=False)
            p_elem.insert(insert_after, content_run)
            return

    def _fix_author_name_order(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Swap surname-first author to first-name-then-surname.

        e.g., "McCutcheon, Jani" → "Jani McCutcheon"
        """
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return

    def _fix_initial_periods(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Remove periods from author initials (H.L.A. → HLA)."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)

    def _fix_journal_the_prefix(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Remove 'the' from start of journal name."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)

    def _fix_journal_abbreviation(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Replace abbreviated journal name with full name.

        e.g., "UNSWLJ" → "University of New South Wales Law Journal"
        """
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested)
                return

    def _fix_journal_italics(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Add italics to journal name.

        Same split-run technique as case name italics — finds the journal name
        text and wraps it in an italic run.
        """
        journal_name = issue.current
        if not journal_name:
            return

        for t_elem in self._get_text_elements(fn_elem):
            text = t_elem.text
            if not text or journal_name not in text:
                continue

            r_elem = t_elem.getparent()
            if r_elem is None:
                continue
            if r_elem.find(f"{{{W_NS}}}footnoteRef") is not None:
                continue

            rpr = r_elem.find(f"{{{W_NS}}}rPr")
            if rpr is not None and rpr.find(f"{{{W_NS}}}i") is not None:
                continue  # Already italic

            idx = text.find(journal_name)
            if idx < 0:
                continue

            p_elem = r_elem.getparent()
            if p_elem is None:
                continue
            r_index = list(p_elem).index(r_elem)

            before_text = text[:idx]
            target = text[idx:idx + len(journal_name)]
            after_text = text[idx + len(journal_name):]

            new_elements: list[etree._Element] = []
            if before_text:
                new_elements.append(self._make_run(before_text, rpr, italic=False))
            new_elements.append(self._make_run(target, rpr, italic=True))
            if after_text:
                new_elements.append(self._make_run(after_text, rpr, italic=False))

            for i, new_r in enumerate(new_elements):
                if i == 0:
                    p_elem.remove(r_elem)
                    p_elem.insert(r_index, new_r)
                else:
                    p_elem.insert(r_index + i, new_r)
            return

    def _fix_book_title_quotes(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Remove quotes from book title (books use italics not quotes)."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                # Remove smart double quotes (U+201C left, U+201D right)
                t_elem.text = t_elem.text.replace("“", "")
                t_elem.text = t_elem.text.replace("”", "")
                # Remove straight double quotes (only around text)
                t_elem.text = regex.sub(r'"([^"]+)"', r"\1", t_elem.text)

    def _fix_book_title_italics(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Add italics to book title.

        Same split-run technique as case name / legislation title italics.
        """
        title = issue.current
        if not title:
            return

        for t_elem in self._get_text_elements(fn_elem):
            text = t_elem.text
            if not text or title not in text:
                continue

            r_elem = t_elem.getparent()
            if r_elem is None:
                continue
            if r_elem.find(f"{{{W_NS}}}footnoteRef") is not None:
                continue

            rpr = r_elem.find(f"{{{W_NS}}}rPr")
            if rpr is not None and rpr.find(f"{{{W_NS}}}i") is not None:
                continue  # Already italic

            idx = text.find(title)
            if idx < 0:
                continue

            p_elem = r_elem.getparent()
            if p_elem is None:
                continue
            r_index = list(p_elem).index(r_elem)

            before_text = text[:idx]
            target = text[idx:idx + len(title)]
            after_text = text[idx + len(title):]

            new_elements: list[etree._Element] = []
            if before_text:
                new_elements.append(self._make_run(before_text, rpr, italic=False))
            new_elements.append(self._make_run(target, rpr, italic=True))
            if after_text:
                new_elements.append(self._make_run(after_text, rpr, italic=False))

            for i, new_r in enumerate(new_elements):
                if i == 0:
                    p_elem.remove(r_elem)
                    p_elem.insert(r_index, new_r)
                else:
                    p_elem.insert(r_index + i, new_r)
            return

    def _fix_text_replace(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Generic fix: find issue.current in footnote text and replace with issue.suggested."""
        if not issue.current or not issue.suggested:
            return
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text and issue.current in t_elem.text:
                t_elem.text = t_elem.text.replace(issue.current, issue.suggested, 1)
                return
        # Fallback: text may span multiple runs
        self._cross_run_text_replace(fn_elem, issue.current, issue.suggested)

    def _fix_case_name_quotes(self, fn_elem: etree._Element, issue: Issue) -> None:
        """Remove quotes from case name (case names use italics, not quotes)."""
        for t_elem in self._get_text_elements(fn_elem):
            if t_elem.text:
                t_elem.text = t_elem.text.replace("“", "")
                t_elem.text = t_elem.text.replace("”", "")
                t_elem.text = regex.sub(r'"([^"]*v[^"]*)"', r'\1', t_elem.text)
