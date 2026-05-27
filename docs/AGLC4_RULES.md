# CiteFix — AGLC4 Rule Specifications

This document encodes AGLC4 rules as machine-testable specifications. Each rule has:
- The AGLC4 rule number
- What's correct
- Common student/clerk errors
- Test examples (input → expected output)

---

## 1. General Rules

### Rule 1.1 — Footnotes
- Every source citation goes in a footnote (superscript number in body text)
- Footnote numbers appear AFTER punctuation (after full stop, comma, closing quote)
- Each footnote ends with a full stop

```
ERROR:   Mabo v Queensland (No 2) (1992) 175 CLR 1, 42
FIXED:   Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.
RULE:    Append "." if missing at end of footnote
```

### Rule 1.3 — Pinpoint References
- Use comma + space + page/paragraph number
- NO "p.", "pp.", "at", "page", "para", "paragraph"
- For paragraph numbers: [X] (square brackets) for medium-neutral citations
- For page numbers: just the number

```
ERROR:   Mabo v Queensland (No 2) (1992) 175 CLR 1 at p. 42.
FIXED:   Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.

ERROR:   Mabo v Queensland (No 2) (1992) 175 CLR 1 at page 42.
FIXED:   Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.

ERROR:   Palmer v Ayres (2017) 259 CLR 478 at pp 487-490.
FIXED:   Palmer v Ayres (2017) 259 CLR 478, 487–490.
RULE:    Remove "at", "p.", "pp.", "page". Replace hyphen with en-dash for ranges.
```

### Rule 1.4 — Subsequent References

#### 1.4.1 — Ibid
- Use "Ibid" (capitalised, italicised) when citing the SAME source as the IMMEDIATELY PRECEDING footnote
- If same source but different pinpoint: "Ibid 55." (Ibid + space + new pinpoint)
- If same source AND same pinpoint: just "Ibid."
- Ibid can ONLY refer to the immediately preceding footnote — not two footnotes back

```
FN 3:    Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.
FN 4:    Mabo v Queensland (No 2) (1992) 175 CLR 1, 55.   ← SHOULD BE: Ibid 55.
FN 5:    Mabo v Queensland (No 2) (1992) 175 CLR 1, 55.   ← SHOULD BE: Ibid.
FN 6:    Some other source.
FN 7:    Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.   ← NOT Ibid (fn 6 broke the chain)
```

#### 1.4.2 — Subsequent references (n X)
- When citing a source previously cited (but NOT immediately preceding), use short title + (n X)
- Short title: shortened version of the case name or author surname
- Format: Short title (n X) pinpoint.

```
FN 3:    Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.   ← first citation (full)
FN 6:    ... other sources ...
FN 8:    Mabo (n 3) 55.                                     ← subsequent reference
```

For cases: use first party name as short title
For legislation: use short Act name
For articles/books: use author surname

---

## 2. Cases (AGLC4 Part 2)

### Rule 2.1 — Case Name
- Italicise the ENTIRE case name including "(No 2)" etc
- Use "v" (lowercase, italicised) not "vs", "vs.", "V", or "versus"
- Omit "The" at the start unless it's essential to meaning

```
ERROR:   Mabo vs Queensland (No 2) (1992) 175 CLR 1, 42.
FIXED:   Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.

ERROR:   MABO V QUEENSLAND (NO 2) (1992) 175 CLR 1, 42.
FIXED:   Mabo v Queensland (No 2) (1992) 175 CLR 1, 42.
RULE:    Case names are italicised, title case. "v" is lowercase.
```

### Rule 2.2 — Year and Report Series

#### Round brackets ( ) for year
Use round brackets when the YEAR is needed to identify the volume (year-of-decision reports).
These report series use round brackets:
- CLR (Commonwealth Law Reports)
- ALJR (Australian Law Journal Reports)
- ALR (Australian Law Reports) — when cited by year not volume
- NSWLR, VR, SASR, WAR, ACTLR, NTLR, NTR
- AC, QB, Ch (English reports)

#### Square brackets [ ] for year
Use square brackets when the year IS the volume identifier (sequential volume reports).
These report series use square brackets:
- FCA, FCAFC, FamCA, FamCAFC (Federal Court)
- HCA (High Court medium neutral)
- NSWSC, NSWCA, NSWCCA
- QCA, QSC, QDC
- VSC, VSCA
- WASC, WASCA
- SASC, SASCFC
- TASSC, TASCCA
- ACTSC, ACTCA
- NTSC, NTCA
- FLC (Family Law Cases)

```
ERROR:   Mabo v Queensland (No 2) [1992] 175 CLR 1.
FIXED:   Mabo v Queensland (No 2) (1992) 175 CLR 1.
REASON:  CLR uses round brackets (year-of-decision series).

ERROR:   Palmer v Ayres [2017] HCA 5.
CORRECT: Palmer v Ayres [2017] HCA 5.
REASON:  HCA (medium neutral) uses square brackets.

ERROR:   Smith v Jones (2023) NSWSC 456.
FIXED:   Smith v Jones [2023] NSWSC 456.
REASON:  NSWSC (medium neutral) uses square brackets.
```

### Rule 2.3 — Volume and Starting Page
- Volume number comes between year and report series: (1992) 175 CLR 1
- Starting page after report series abbreviation: CLR 1
- Pinpoint after comma: CLR 1, 42
- For medium-neutral citations: paragraph pinpoints in square brackets [42]

```
ERROR:   Palmer v Ayres [2017] HCA 5 at [31].
FIXED:   Palmer v Ayres [2017] HCA 5, [31].
RULE:    Remove "at", keep square bracket pinpoint for medium-neutral.

ERROR:   Palmer v Ayres [2017] HCA 5 at para 31.
FIXED:   Palmer v Ayres [2017] HCA 5, [31].
```

### Rule 2.4 — Unreported Decisions (Medium Neutral)
- Format: Case Name [Year] Court Identifier Number
- No volume, no report series page — just the court identifier
- Paragraph pinpoints in square brackets: [42]

```
CORRECT: Roadshow Films Pty Ltd v iiNet Ltd [2012] HCA 16, [5].
```

---

## 3. Legislation (AGLC4 Part 3)

### Rule 3.1 — Acts of Parliament
- Italicise BOTH the title AND the year
- Jurisdiction abbreviation in round brackets (NOT italicised)
- Commonwealth: (Cth)
- States: (NSW), (Vic), (Qld), (WA), (SA), (Tas), (ACT), (NT)

```
ERROR:   Limitation Act 2005 (WA) s 14(1).
FIXED:   Limitation Act 2005 (WA) s 14(1).
NOTE:    "Limitation Act 2005" must be italicised. "(WA)" NOT italicised.

ERROR:   Corporations Act 2001 (Cth), Section 180(1).
FIXED:   Corporations Act 2001 (Cth) s 180(1).
RULES:   - "Section" → "s" (abbreviate)
         - Remove comma before section pinpoint
         - Italicise title and year
```

### Rule 3.2 — Section Pinpoints
- Use "s" for section (not "section", "sec", "sec.", "§")
- Use "ss" for multiple sections
- Use "reg" for regulation, "regs" for multiple
- Use "r" for rule, "rr" for multiple
- Use "cl" for clause, "cll" for multiple
- Use "sch" for schedule
- Use "pt" for part, "div" for division
- NO comma between jurisdiction and section pinpoint

```
ERROR:   Corporations Act 2001 (Cth), § 180(1).
FIXED:   Corporations Act 2001 (Cth) s 180(1).

ERROR:   Fair Work Act 2009 (Cth) section 394.
FIXED:   Fair Work Act 2009 (Cth) s 394.

ERROR:   Transfer of Land Act 1893 (WA), Section 68(1A).
FIXED:   Transfer of Land Act 1893 (WA) s 68(1A).
```

### Rule 3.3 — Delegated Legislation (Regulations, Rules)
- Same format: Title Year (Jurisdiction) pinpoint
- Italicise title and year

```
CORRECT: Family Law Rules 2004 (Cth) r 13.04.
CORRECT: Legal Profession Uniform General Rules 2015 (NSW) r 42.
```

---

## 4. Journal Articles (AGLC4 Chapter 5 — Secondary Sources)

### Rule 5.1 — Journal Articles
- Format: Author, 'Title' (Year) Volume Journal Name Starting Page, Pinpoint.
- Title in SINGLE quotes (not double quotes)
- Journal name in FULL (not abbreviated), italicised
- Year in round brackets
- Author name: First name then surname (not surname first)

```
ERROR:   McCutcheon, Jani, "The Vanishing Author in Computer-Generated Works" (2013) 36 UNSW Law Journal 915.
FIXED:   Jani McCutcheon, 'The Vanishing Author in Computer-Generated Works' (2013) 36 University of New South Wales Law Journal 915.
RULES:   - Author: first name then surname (not "Surname, First")
         - Single quotes around title (not double)
         - Full journal name, italicised

ERROR:   J McCutcheon, "The Vanishing Author" (2013) 36 UNSWLJ 915, at p. 920.
FIXED:   Jani McCutcheon, 'The Vanishing Author in Computer-Generated Works' (2013) 36 University of New South Wales Law Journal 915, 920.
RULES:   - Use full first name if known (not initial)
         - Single quotes
         - Full journal name
         - Remove "at p."
NOTE:    CiteFix may not know the author's full first name — flag for manual review.
```

### Rule 5.2 — Books
- Format: Author, Title (Publisher, Edition, Year) Pinpoint.
- Title italicised
- Publisher, edition, year in round brackets
- "ed" for edition (not "edn", "edition")
- For edited books: Editor (ed) or Editors (eds)

```
ERROR:   Mark Leeming, "Authority to Decide" (Federation Press, 2nd edition, 2020) p 45.
FIXED:   Mark Leeming, Authority to Decide (Federation Press, 2nd ed, 2020) 45.
RULES:   - Book title italicised, no quotes
         - "edition" → "ed"
         - Remove "p" from pinpoint

CORRECT: Robin Creyke, Matthew Groves and John McMillan, Control of Government Action: Text, Cases and Commentary (LexisNexis Butterworths, 5th ed, 2019) 420.
```

### Rule 5.3 — Chapters in Edited Books
- Format: Author, 'Chapter Title' in Editor (ed), Book Title (Publisher, Edition, Year) Starting Page, Pinpoint.

```
CORRECT: Andrew Stewart, 'The Evolution of Labour Law' in Andrew Stewart et al (eds), Creighton and Stewart's Labour Law (Federation Press, 6th ed, 2016) 1, 15.
```

---

## 5. Common Cross-Cutting Errors

### Quotation marks
- AGLC4 uses SINGLE quotes for article titles, chapter titles, speech titles
- Double quotes only for quotes WITHIN quotes
- Smart/curly quotes are acceptable

```
ERROR:   "The Vanishing Author in Computer-Generated Works"
FIXED:   'The Vanishing Author in Computer-Generated Works'
```

### En-dash for page/paragraph ranges
- Use en-dash (–) not hyphen (-) for ranges
- Pages 487–490, not 487-490

```
ERROR:   487-490
FIXED:   487–490
```

### Spacing
- One space between all elements
- No double spaces
- No space before pinpoint comma: "CLR 1, 42" not "CLR 1 , 42"

### Jurisdiction abbreviations (complete list)
```
Commonwealth:       (Cth)
New South Wales:    (NSW)
Victoria:           (Vic)
Queensland:         (Qld)
Western Australia:  (WA)
South Australia:    (SA)
Tasmania:           (Tas)
ACT:                (ACT)
Northern Territory: (NT)
New Zealand:        (NZ)
United Kingdom:     (UK)
```

### Report series requiring ROUND brackets for year
```
CLR, ALJR, ALR, FCR, FLR, NSWLR, QdR, VR, SASR, WAR, TasR,
SR (NSW), SR (Qld), SR (WA), WALR, AC, QB, KB, Ch, All ER,
WLR, ICR, Cr App R, BCLC, Lloyd's Rep
```

### Report series / identifiers requiring SQUARE brackets for year
```
HCA, FCAFC, FCA, FamCA, FamCAFC, NSWSC, NSWCA, NSWCCA,
NSWDC, NSWLEC, QCA, QSC, QDC, QMC, VSC, VSCA, VCC,
WASC, WASCA, WADC, WAMW, SASC, SASCFC, SADC, SAET,
TASSC, TASFC, TASCCA, ACTSC, ACTCA, NTSC, NTCA, NZSupC,
NZSC, NZCA, NZHC, FLC, FMCA, FCCA, AATA, AAT,
Qd R (Queensland Reports — year-organised)
```

---

## 6. Error Catalogue — Common Mistakes to Detect

| # | Error | Example | Fix |
|---|-------|---------|-----|
| 1 | Case name not italicised | Mabo v Queensland | *Mabo v Queensland* |
| 2 | "vs" or "vs." instead of "v" | Smith vs Jones | Smith v Jones |
| 3 | Wrong year bracket type | [1992] 175 CLR 1 | (1992) 175 CLR 1 |
| 4 | "p." or "at" in pinpoint | CLR 1 at p. 42 | CLR 1, 42 |
| 5 | "section" not abbreviated | section 14(1) | s 14(1) |
| 6 | Legislation not italicised | Limitation Act 2005 | *Limitation Act 2005* |
| 7 | Double quotes on title | "Title" | 'Title' |
| 8 | Missing full stop | CLR 1, 42 | CLR 1, 42. |
| 9 | Hyphen instead of en-dash | 487-490 | 487–490 |
| 10 | Should be Ibid | Full cite repeated from prev fn | Ibid / Ibid 55. |
| 11 | Wrong Ibid (not consecutive) | Ibid (but fn 5 cited something else) | Full cite or (n X) |
| 12 | "edition" not abbreviated | 2nd edition | 2nd ed |
| 13 | Surname-first author | McCutcheon, Jani | Jani McCutcheon |
| 14 | Journal name abbreviated | UNSWLJ | University of New South Wales Law Journal |
| 15 | Comma before section | (Cth), s 180 | (Cth) s 180 |
| 16 | "§" instead of "s" | § 14(1) | s 14(1) |
| 17 | No space after "s" | s14(1) | s 14(1) |
| 18 | Missing jurisdiction | Corporations Act 2001 s 180 | Corporations Act 2001 (Cth) s 180 |
| 19 | "para" or "paragraph" | para 31 | [31] |
| 20 | Double spacing | CLR  1 | CLR 1 |
