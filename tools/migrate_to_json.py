"""One-time migration of a year's data files from .js to .json (code is .js, data is .json).

  python tools/migrate_to_json.py 2026 [--data-dir PATH]

Reads <year>/hsa_data_<year>.js and hsa_decisions_<year>.js, writes the .json files next to them,
and moves the old .js files into <year>/backups/<today>/. Nothing is deleted. A year that already
has the .json files is left alone.
"""

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsa_paths import data_dir_or_exit  # noqa: E402

DATA_NAMES = ["DATA_AS_OF", "YEAR_CONFIG", "ORDERS", "MEDICAL", "ALL_ORDERS", "SKIPPED_ORDERS", "ASIN_INFO"]


def evaluate(js_text, names):
    """Run the old data file in a browser and return the named values as JSON-ready data."""
    from playwright.sync_api import sync_playwright

    script = "([t, names]) => { const f = new Function(t + '; return {' + names.map(n => n + ': (typeof ' + n + ' !== \"undefined\" ? ' + n + ' : undefined)').join(',') + '}'); return f(); }"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            return browser.new_page().evaluate(script, [js_text, names])
        finally:
            browser.close()


def migrate(year_dir, year):
    data_js = year_dir / f"hsa_data_{year}.js"
    dec_js = year_dir / f"hsa_decisions_{year}.js"
    data_json = year_dir / f"hsa_data_{year}.json"
    dec_json = year_dir / f"hsa_decisions_{year}.json"
    backups = year_dir / "backups" / date.today().isoformat()
    done = []
    if data_js.exists() and not data_json.exists():
        values = evaluate(data_js.read_text(encoding="utf-8"), DATA_NAMES)
        data_json.write_text(json.dumps({k: v for k, v in values.items() if v is not None}, ensure_ascii=False, indent=1), encoding="utf-8")
        done.append(data_js)
    if dec_js.exists() and not dec_json.exists():
        values = evaluate(dec_js.read_text(encoding="utf-8"), ["SAVED_DECISIONS"])
        dec_json.write_text(json.dumps(values["SAVED_DECISIONS"] or {}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        done.append(dec_js)
    backups.mkdir(parents=True, exist_ok=True) if done else None
    for old in done:
        shutil.move(str(old), str(backups / old.name))  # the .json is already written, so the old file only moves
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("year")
    ap.add_argument("--data-dir")
    args = ap.parse_args(argv)
    year_dir = data_dir_or_exit(args.data_dir) / args.year
    done = migrate(year_dir, args.year)
    print(f"migrated {len(done)} file(s)" if done else "nothing to migrate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
