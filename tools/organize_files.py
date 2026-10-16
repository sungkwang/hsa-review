"""Names your documents so the name says what each one is, and keeps them all in <year>/receipts/.

Names look like  YYYY-MM-DD_type_source_detail.ext  with five types: order, bill, receipt, eob, letter.
Sorting by name sorts by date, and searching for _bill_ or _letter_ shows one type.

By default this only prints the plan and changes nothing. Add --confirm to rename or move.
Files are never deleted. Every run is logged for --undo. Duplicates are found by file hash, not by name.
The year comes from the document date; a file whose download year differs is flagged. A file that cannot
be identified keeps its name (hsa.py status lists it as "not identified"). Images are not read here
(no text layer), so they keep their names too.

Your data folder comes from --data-dir, HSA_DATA_DIR, or the setup config; never the code folder.

  python tools/organize_files.py INBOX --year 2026     # plan: move new files from INBOX into receipts/
  python tools/organize_files.py --year 2026           # plan: rename what is already in receipts/
  add --confirm to do it, or run  python tools/organize_files.py --undo  to put the last run back
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsa_paths import RECEIPT_NAME_RE, data_dir_or_exit, year_paths  # noqa: E402

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
ORDER_RE = re.compile(r"\d{3}-\d{7}-\d{7}")
DATE_PATTERNS = [
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})", re.I), lambda m: (int(m[3]), MONTHS[m[1].lower()], int(m[2]))),
    (re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"), lambda m: (int(m[3]), int(m[1]), int(m[2]))),
]
FILE_TYPES = {".pdf", ".png", ".jpg", ".jpeg", ".heic"}


def read_text(path):
    if path.suffix.lower() != ".pdf":
        return None
    try:
        from pypdf import PdfReader

        return "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    except Exception:
        return ""


def find_date(text):
    for pattern, build in DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                y, mo, d = build(m)
                return datetime(y, mo, d).date()
            except ValueError:
                continue
    return None


def slug(text, limit=40):
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9]+", "-", text)).strip("-")[:limit] or "unknown"


def source_line(text):
    """The first line that looks like a name: two or more words, no colon, mostly letters."""
    for line in text.splitlines():
        line = line.strip()
        if len(line.split()) >= 2 and ":" not in line and sum(c.isalpha() for c in line) >= 0.6 * len(line):
            return line
    return ""


def classify(path):
    """Return (type, date, source, detail, reason). type is None when the file cannot be identified."""
    text = read_text(path)
    if text is None:
        return None, None, "", "", "an image has no text layer; a person or a model must read it"
    if not text.strip():
        return None, None, "", "", "the PDF has no text layer (a scan)"
    low = text.lower()
    date = find_date(text)
    if ORDER_RE.search(text) and "amazon" in low:
        kind, source, detail = "order", "amazon", ORDER_RE.search(text).group(0)
    elif "explanation of benefits" in low or "this is not a bill" in low:
        kind, source, detail = "eob", slug(source_line(text)), "statement"
    elif "medical necessity" in low:
        kind, source, detail = "letter", slug(source_line(text)), "LMN"
    elif any(w in low for w in ("amount due", "statement date", "date of service")):
        kind, source, detail = "bill", slug(source_line(text)), "visit"
    elif any(w in low for w in ("receipt", "customer copy", "approval code", "subtotal")):
        kind, source, detail = "receipt", slug(source_line(text)), "purchase"
    else:
        return None, date, "", "", "the type is unclear (not an order, bill, receipt, EOB, or letter)"
    if date is None:
        return None, None, source, detail, f"looks like a {kind} but no date was found"
    return kind, date, source, detail, ""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def known_hashes(root, skip_dir=None):
    seen = {}
    for year_dir in sorted(Path(root).glob("[0-9][0-9][0-9][0-9]")):
        receipts = year_dir / "receipts"
        if receipts.is_dir() and receipts != skip_dir:
            for f in receipts.iterdir():
                if f.is_file():
                    seen[sha(f)] = f
    return seen


def plan(root, year, inbox=None):
    in_place = inbox is None
    inbox = year_paths(root, year).receipts if in_place else Path(inbox)
    seen = known_hashes(root, skip_dir=inbox if in_place else None)
    rows, taken = [], set()
    files = sorted(p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in FILE_TYPES) if inbox.is_dir() else []
    for f in files:
        digest = sha(f)
        if digest in seen:
            rows.append({"src": f, "dst": None, "note": f"duplicate of {seen[digest].name}; left where it is"})
            continue
        seen[digest] = f
        kind, date, source, detail, reason = classify(f)
        download_year = datetime.fromtimestamp(f.stat().st_mtime).year
        doc_year = str(date.year) if date else (year if in_place else str(download_year))
        if kind and re.match(RECEIPT_NAME_RE, f.name) and in_place:
            rows.append({"src": f, "dst": f, "note": "already named"})
            continue
        name = f"{date.isoformat()}_{kind}_{source}_{slug(detail)}{f.suffix.lower()}" if kind else f.name
        dst = year_paths(root, doc_year).receipts / name
        n = 2
        while dst in taken or (dst.exists() and dst != f):
            dst = dst.with_name(f"{dst.stem}-{n}{dst.suffix}")
            n += 1
        taken.add(dst)
        note = f"not identified: {reason}" if not kind else ""
        if kind and str(download_year) != doc_year and not in_place:
            note = f"document year {doc_year} differs from download year {download_year}"
        elif kind and in_place and doc_year != str(year):
            note = f"document year {doc_year}; it moves to the {doc_year} receipts folder"
        rows.append({"src": f, "dst": dst, "note": note})
    return rows


def show(rows, root):
    print(f"{len(rows)} file(s)")
    for r in rows:
        if r["dst"] is None:
            target = "(not moved)"
        elif r["dst"] == r["src"]:
            target = "(keeps its name)"
        else:
            target = r["dst"].relative_to(root).as_posix()
        print(f"  {r['src'].name}  ->  {target}" + (f"   [{r['note']}]" if r["note"] else ""))


def move(rows, root, year):
    log_dir = year_paths(root, year).app / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    moves = []
    for r in rows:
        if r["dst"] is None or r["dst"] == r["src"]:
            continue
        r["dst"].parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(r["src"]), str(r["dst"]))
        moves.append({"src": str(r["src"]), "dst": str(r["dst"])})
    log = log_dir / f"organize-{datetime.now():%Y%m%d-%H%M%S}.json"
    log.write_text(json.dumps(moves, indent=1), encoding="utf-8")
    print(f"changed {len(moves)} file(s); log: {log.name}")


def undo(root):
    logs = sorted(Path(root).glob("[0-9][0-9][0-9][0-9]/_app/logs/organize-*.json"), key=lambda p: p.name)
    if not logs:
        print("nothing to undo")
        return 1
    log = logs[-1]
    back = 0
    for m in reversed(json.loads(log.read_text(encoding="utf-8"))):
        src, dst = Path(m["src"]), Path(m["dst"])
        if dst.exists() and not src.exists():
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
            back += 1
        else:
            print(f"  skipped {dst.name}: already moved or the original place is taken")
    log.rename(log.with_suffix(".undone"))
    print(f"put back {back} file(s) from {log.name}")
    return 0


def main(argv=None, root=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inbox", nargs="?", help="a folder with new files to move into receipts/ (omit to rename what is already there)")
    ap.add_argument("--year", default=str(datetime.now().year))
    ap.add_argument("--confirm", action="store_true", help="do it (default: print the plan only)")
    ap.add_argument("--undo", action="store_true", help="reverse the last confirmed run")
    ap.add_argument("--data-dir", help="your data folder (default: from setup or HSA_DATA_DIR)")
    args = ap.parse_args(argv)
    root = Path(root) if root else data_dir_or_exit(args.data_dir)
    if args.undo:
        return undo(root)
    rows = plan(root, args.year, args.inbox)
    show(rows, root)
    if args.confirm:
        move(rows, root, args.year)
    else:
        print("plan only; nothing was changed. Add --confirm to go ahead.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
