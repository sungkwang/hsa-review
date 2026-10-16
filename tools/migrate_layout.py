"""One-time move of a data folder to the simple layout.

  <year>/receipts/        all your documents, one level, named YYYY-MM-DD_type_source_detail.ext
  <year>/reports/         claim PDF, evidence PDF, CSV exports
  <year>/decisions.json   your choices
  <year>/_app/            orders, images, product cache, backups, logs (not for editing)

  python tools/migrate_layout.py [--data-dir PATH]            # prints old -> new for every file; changes nothing
  python tools/migrate_layout.py --confirm [--data-dir PATH]  # backs up first, checks the backup, then moves

The backup is a full copy of the data folder next to it (<folder>.backup-<date>). Each file is compared by
size and hash; if anything differs, nothing is moved. Nothing is deleted.
"""

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsa_paths import APP_README, data_dir_or_exit  # noqa: E402
from organize_files import FILE_TYPES, classify, slug  # noqa: E402

INVOICE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{3}-\d{7}-\d{7})_Invoice\.pdf$")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_copy(src, dst):
    """Return a list of differences between two folders (empty means an exact copy)."""
    problems = []
    a = {p.relative_to(src).as_posix(): p for p in Path(src).rglob("*") if p.is_file()}
    b = {p.relative_to(dst).as_posix(): p for p in Path(dst).rglob("*") if p.is_file()}
    for name in sorted(set(a) - set(b)):
        problems.append(f"missing in the backup: {name}")
    for name in sorted(set(a) & set(b)):
        if a[name].stat().st_size != b[name].stat().st_size or _sha(a[name]) != _sha(b[name]):
            problems.append(f"differs: {name}")
    return problems


def legacy_years(root):
    return sorted(d.name for d in Path(root).glob("[0-9][0-9][0-9][0-9]") if (d / f"hsa_data_{d.name}.json").exists() and not (d / "_app" / "data.json").exists())


def plan_year(root, year):
    """List the moves for one year as dicts: src, dst, note. Also returns the new MEDICAL src names."""
    y = Path(root) / year
    moves = []

    def add(src, dst, note=""):
        moves.append({"src": src, "dst": dst, "note": note})

    data_file = y / f"hsa_data_{year}.json"
    medical = {}
    try:
        for entry in json.loads(data_file.read_text(encoding="utf-8")).get("MEDICAL", []):
            if entry.get("src"):
                medical[entry["src"]] = entry
    except (OSError, ValueError):
        pass
    add(data_file, y / "_app" / "data.json")
    for old, new in ((f"hsa_decisions_{year}.json", "decisions.json"),):
        if (y / old).exists():
            add(y / old, y / new)
    for old, new in ((f"asin_info_{year}.json", "_app/product_cache.json"), (f"product_decisions_{year}.json", "_app/product_decisions.json"), ("backups", "_app/backups")):
        if (y / old).exists():
            add(y / old, y / new)
    for f in sorted(y.glob("*.csv")):
        add(f, y / "reports" / f.name)
    renames = {}
    for f in sorted(p for p in y.iterdir() if p.is_file() and p.suffix.lower() in FILE_TYPES):
        m = INVOICE_RE.match(f.name)
        note = ""
        if m:
            name = f"{m.group(1)}_order_amazon_{m.group(2)}.pdf"
        elif f.name in medical:
            e = medical[f.name]
            name = f"{e['date']}_bill_{slug(e.get('provider', 'medical'), 48)}_visit{f.suffix.lower()}"
        else:
            kind, d, source, detail, reason = classify(f)
            name = f"{d.isoformat()}_{kind}_{source}_{slug(detail)}{f.suffix.lower()}" if kind else f.name
            note = "" if kind else f"not identified: {reason}"
        add(f, y / "receipts" / name, note)
        renames[f.name] = name
    return moves, renames


def plan(root):
    root = Path(root)
    years = legacy_years(root)
    out = []
    for i, year in enumerate(years):
        moves, renames = plan_year(root, year)
        out.append({"year": year, "moves": moves, "renames": renames})
    images = root / "images"
    image_moves = []
    if images.is_dir() and years:
        for year in years:
            image_moves.append({"src": images, "dst": root / year / "_app" / "images", "note": "moved" if len(years) == 1 else "copied (more than one year)"})
    return out, image_moves


def show(years_plan, image_moves, root, backup):
    print(f"Data folder: {root}\nBackup would go to: {backup}\n")
    if not years_plan:
        print("Nothing to migrate: no year folder uses the older layout.")
        return
    for yp in years_plan:
        print(f"{yp['year']}:")
        for m in yp["moves"]:
            print(f"  {m['src'].relative_to(root).as_posix()}  ->  {m['dst'].relative_to(root).as_posix()}" + (f"   [{m['note']}]" if m["note"] else ""))
    for m in image_moves:
        print(f"  {m['src'].relative_to(root).as_posix()}/  ->  {m['dst'].relative_to(root).as_posix()}/   [{m['note']}]")
    print("\nAlso: _app/README.txt is created, and receipt names used in data.json are updated.")


def migrate(root, backup=None):
    root = Path(root)
    backup = Path(backup) if backup else root.with_name(f"{root.name}.backup-{date.today().isoformat()}")
    years_plan, image_moves = plan(root)
    if not years_plan:
        return [], backup
    if backup.exists():
        raise SystemExit(f"The backup folder already exists: {backup}. Move it away or rename it, then run again.")
    shutil.copytree(root, backup)
    problems = verify_copy(root, backup)
    if problems:
        raise SystemExit("The backup does not match the original, so nothing was moved:\n  " + "\n  ".join(problems[:10]))
    done = []
    for yp in years_plan:
        y = root / yp["year"]
        (y / "_app").mkdir(exist_ok=True)
        (y / "_app" / "README.txt").write_text(APP_README, encoding="utf-8")
        for m in yp["moves"]:
            m["dst"].parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(m["src"]), str(m["dst"]))
            done.append(m)
        data_file = y / "_app" / "data.json"
        data = json.loads(data_file.read_text(encoding="utf-8"))
        for entry in data.get("MEDICAL", []):
            if entry.get("src") in yp["renames"]:
                entry["src"] = yp["renames"][entry["src"]]
        data_file.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        (y / "reports").mkdir(exist_ok=True)
        (y / "receipts").mkdir(exist_ok=True)
    if image_moves:
        if len(image_moves) == 1:
            shutil.move(str(image_moves[0]["src"]), str(image_moves[0]["dst"]))
        else:
            for m in image_moves:
                shutil.copytree(m["src"], m["dst"])
    return done, backup


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir")
    ap.add_argument("--confirm", action="store_true", help="back up, check the backup, then move (default: print the plan only)")
    args = ap.parse_args(argv)
    root = data_dir_or_exit(args.data_dir)
    backup = root.with_name(f"{root.name}.backup-{date.today().isoformat()}")
    years_plan, image_moves = plan(root)
    show(years_plan, image_moves, root, backup)
    if not args.confirm:
        print("\nplan only; nothing was changed. Add --confirm to back up and move.")
        return 0
    done, backup = migrate(root)
    print(f"\nbacked up and verified: {backup}\nmoved {len(done)} item(s). Run: python tools/hsa.py status")
    return 0


if __name__ == "__main__":
    sys.exit(main())
