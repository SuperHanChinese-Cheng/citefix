"""Compare original vs fixed document footnotes side by side."""
import sys
sys.path.insert(0, "src")

from citefix.extractor import extract_footnotes


def fmt_runs(runs):
    """Format runs showing italic markers."""
    parts = []
    for r in runs:
        if r.italic:
            parts.append(f"*{r.text}*")
        else:
            parts.append(r.text)
    return "".join(parts)


orig_path = r"C:\Users\cheng\Downloads\citefix_test_document.docx"
fixed_path = r"C:\Users\cheng\Downloads\citefix_fixed_v4.docx"

with open(orig_path, "rb") as f:
    orig_fns = extract_footnotes(f.read())
with open(fixed_path, "rb") as f:
    fixed_fns = extract_footnotes(f.read())

orig_map = {fn.index: fn for fn in orig_fns}
fixed_map = {fn.index: fn for fn in fixed_fns}

all_ids = sorted(set(orig_map.keys()) | set(fixed_map.keys()))

for fid in all_ids:
    orig = orig_map.get(fid)
    fixed = fixed_map.get(fid)
    if not orig or not fixed:
        continue

    orig_fmt = fmt_runs(orig.runs)
    fixed_fmt = fmt_runs(fixed.runs)

    changed = orig.plain_text != fixed.plain_text or orig_fmt != fixed_fmt
    marker = "CHANGED" if changed else "OK"

    print(f"--- FN {fid} [{marker}] ---")
    if changed:
        print(f"  ORIG:  {orig_fmt}")
        print(f"  FIXED: {fixed_fmt}")
    else:
        print(f"  {fixed_fmt}")
    print()
