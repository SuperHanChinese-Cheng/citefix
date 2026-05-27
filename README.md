# CiteFix — AGLC4 Citation Auto-Formatter

Upload a Word document. Get back the same document with all AGLC4 footnote errors fixed.

## What it does

- Scans every footnote in your .docx file
- Detects AGLC4 formatting errors (wrong brackets, missing italics, bad pinpoints, etc.)
- Fixes them automatically and returns the corrected document
- Flags ambiguous citations for manual review

## What it catches

- Case names not italicised
- Wrong bracket type around the year (round vs square)
- "vs" instead of "v"
- "p." or "at" in pinpoints
- "section" instead of "s" in legislation
- Double quotes instead of single quotes on article titles
- Missing full stops at end of footnotes
- Missing Ibid for consecutive same-source citations
- Hyphens instead of en-dashes in page ranges
- And 20+ more common errors

## Quick Start

```bash
git clone https://github.com/yourname/citefix.git
cd citefix
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn citefix.api:app --reload --port 8000
```

Then POST a .docx to `http://localhost:8000/fix` and get back the fixed file.

## License

MIT
