"""Checks that every medical bill is in the Deductible evidence PDF before you print it.

For the year: every medical entry must have an image that exists, every PDF source must have one image per
page, and every bill, receipt, EOB, or letter in receipts/ must belong to some entry. Files in receipts/ whose
names do not say what they are are listed too (run organize_files.py).

Run:  python tools/check_evidence.py 2026 [--data-dir PATH]
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsa_paths import RECEIPT_NAME_RE, data_dir_or_exit, year_paths  # noqa: E402


def check(data, year):
    """Return (number of medical entries, list of problems)."""
    p = year_paths(data, year)
    doc = json.loads(p.data.read_text(encoding="utf-8"))
    entries = doc.get("MEDICAL", [])
    docs_dir = p.receipts if p.new_layout else p.year_dir  # where the source files live
    base = p.images.parent  # image paths in the data file ("images/...") are relative to this folder
    problems, sources = [], set()
    for e in entries:
        ident, src, thumb = e.get("id", "?"), e.get("src", ""), e.get("thumb", "")
        full = list(e.get("full") or [])
        sources.add(src)
        for img in full or [thumb]:
            if not img or not (base / img).exists():
                problems.append(f"{ident}: image missing: {img or '(none)'}")
        source_file = docs_dir / src
        if src.lower().endswith(".pdf") and source_file.exists():
            try:
                import pypdf

                pages = len(pypdf.PdfReader(source_file).pages)
                if len(full) != pages:
                    problems.append(f"{ident}: {src} has {pages} page(s) but {len(full)} full image(s) listed")
            except ImportError:
                problems.append("pypdf is not installed, so PDF page counts were not checked")
        elif not source_file.exists():
            problems.append(f"{ident}: source file not found: {src}")
    if docs_dir.is_dir():
        for f in sorted(docs_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".heic"} or f.name in sources:
                continue
            m = re.match(RECEIPT_NAME_RE, f.name)
            if m and m.group(1) == "order":
                continue  # an Amazon order summary, not a medical document
            if p.new_layout:
                problems.append(f"{f.name}: " + ("in receipts/ but no medical entry uses it" if m else "not identified (its name does not say what it is); run organize_files.py"))
            elif not f.name.endswith("_Invoice.pdf") and not f.name.startswith("med_"):
                problems.append(f"{f.name}: in the {year} folder but no medical entry uses it")
    return len(entries), problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("year", nargs="?", default="2026")
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)
    count, problems = check(data_dir_or_exit(args.data_dir), args.year)
    print(f"{args.year}: {count} medical entries, {len(problems)} problem(s)")
    for line in problems:
        print("  PROBLEM:", line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
