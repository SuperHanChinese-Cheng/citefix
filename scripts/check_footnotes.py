"""Check footnotes in fixed document."""
import sys
sys.path.insert(0, "src")

from citefix.extractor import extract_footnotes

with open(r"C:\Users\cheng\Downloads\citefix_fixed_output2.docx", "rb") as f:
    fns = extract_footnotes(f.read())

# Show all footnotes with formatting info
for fn in fns:
    if fn.index in range(1, 31):
        print(f"FN {fn.index}: {fn.plain_text}")
        for r in fn.runs:
            tag = "[I]" if r.italic else "[ ]"
            print(f"  {tag} '{r.text}'")
        print()
