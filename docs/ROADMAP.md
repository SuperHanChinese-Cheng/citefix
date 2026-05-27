# CiteFix — Development Roadmap

## Phase 1: Core Pipeline MVP (Weeks 1–2)
> Goal: Upload a .docx → get back fixed .docx with case + legislation errors corrected

### Week 1: Extraction + Case Parser + Legislation Parser
- [ ] Set up project: pyproject.toml, venv, ruff, pytest
- [ ] Implement models.py: Footnote, FootnoteRun (preserves italic/bold), Citation, ParseResult, Issue, FixResult
- [ ] Implement extractor.py: read .docx footnotes.xml via lxml, extract each footnote with formatting info
- [ ] Implement classifier.py: regex-based classification into source types
- [ ] Implement parsers/case.py: parse case citations into structured fields
- [ ] Implement parsers/legislation.py: parse legislation citations into structured fields
- [ ] Implement rules/abbreviations.py: report series → bracket type lookup table
- [ ] Implement rules/jurisdictions.py: jurisdiction abbreviation lookup
- [ ] Write tests for all of the above with real AGLC4 examples

### Week 2: Rule Engine + Rewriter + API
- [ ] Implement rules/validators.py: individual validation functions per rule
- [ ] Implement rules/engine.py: RuleEngine that runs all validators on a parsed citation
- [ ] Implement rules/cross_ref.py: Ibid detection + subsequent reference detection
- [ ] Implement rewriter.py: apply fixes back to .docx footnote XML (preserving all other content)
- [ ] Implement pipeline.py: orchestrate extract → classify → parse → validate → rewrite
- [ ] Implement api.py: FastAPI with POST /upload (multipart .docx) → returns fixed .docx
- [ ] Write end-to-end test: sample_essay.docx with known errors → verify all fixed
- [ ] Generate test fixtures with scripts/generate_test_docx.py

## Phase 2: Secondary Sources + Frontend (Weeks 3–4)

### Week 3: Journal + Book Parsers
- [ ] Implement parsers/journal.py: journal article citation parser
- [ ] Implement parsers/book.py: book + edited book + chapter parser
- [ ] Implement parsers/ibid.py: dedicated Ibid/subsequent reference parser
- [ ] Add validators: single quotes, journal name not abbreviated, author name order, "ed" not "edition"
- [ ] Add cross-reference engine: detect repeated full citations that should be (n X)
- [ ] Expand test suite with secondary source examples

### Week 4: Frontend + Deploy
- [ ] Build frontend: drag-drop upload zone, processing spinner, download button
- [ ] Add output mode toggle: "Clean" vs "Review" (highlighted changes)
- [ ] Review mode: add Word comments explaining each fix ("Changed [1992] to (1992) per AGLC4 rule 2.2")
- [ ] Deploy: Docker container on Railway/Fly.io (backend), Vercel (frontend)
- [ ] Write the LinkedIn post with a 60-second demo video
- [ ] Tag v1.0.0

## Phase 3: Polish + Word Add-in (Weeks 5–8)

### Nice-to-haves
- [ ] LLM fallback: send low-confidence citations to LLM API for classification
- [ ] Report series abbreviation expansion (UNSWLJ → University of New South Wales Law Journal)
- [ ] Composite footnote handling (multiple sources separated by semicolons)
- [ ] Batch upload (multiple .docx files)
- [ ] Microsoft Word Add-in (Office.js sidebar)
- [ ] AGLC5 rule module (when released)
- [ ] Treaty + international materials parser
- [ ] Hansard parser
- [ ] Website/online source parser
