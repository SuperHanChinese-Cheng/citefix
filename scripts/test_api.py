"""Quick script to test the CiteFix API against the test document."""
import httpx
import json
import sys

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"
docx_path = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\cheng\Downloads\citefix_test_document.docx"

with open(docx_path, "rb") as f:
    resp = httpx.post(
        f"{url}/analyze",
        files={"file": ("test.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

if resp.status_code != 200:
    print(f"ERROR: {resp.status_code} {resp.text}")
    sys.exit(1)

data = resp.json()
print(f"Footnotes scanned: {data['footnote_count']}")
print(f"Total issues:      {data['total_issues']}")
print(f"Auto-fixable:      {data['auto_fixable']}")
print(f"Needs review:      {data['needs_review']}")
print()

for iss in data["issues"]:
    sev = iss["severity"].upper()
    fix = "AUTO" if iss["auto_fixable"] else "MANUAL"
    print(f"  FN{iss['footnote']:>2} [{sev:>7}] [{fix:>6}] Rule {iss['rule']}: {iss['description']}")
    if iss["suggested"]:
        suggested = iss["suggested"][:90]
        print(f"           -> {suggested}")
