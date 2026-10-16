"""Finds the user's data folder. The data never lives in this code folder.

Checked in order: --data-dir, the HSA_DATA_DIR environment variable, then
~/.hsa-review/config.json (written by setup). If none is set, stop with a message.
There is deliberately no fallback to the code folder.
"""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

CONFIG = Path.home() / ".hsa-review" / "config.json"
NOT_SET = "No data folder set. Run setup (or pass --data-dir)."


class DataDirError(Exception):
    pass


def default_data_dir():
    """The suggested place for the user's data."""
    base = Path.home() / "Documents" if os.name == "nt" else Path.home()
    return base / "HSA-Review"


def read_config(config=None):
    config = config or CONFIG
    try:
        return json.loads(config.read_text(encoding="utf-8")).get("data_dir")
    except (OSError, ValueError, AttributeError):
        return None


def write_config(path, config=None):
    config = config or CONFIG
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({"data_dir": str(Path(path).expanduser().resolve())}, indent=1), encoding="utf-8")


def data_dir(cli=None, env=None, config=None):
    """Return the data folder as a Path, or raise DataDirError with a plain message."""
    env = os.environ if env is None else env
    for source, value in (("--data-dir", cli), ("HSA_DATA_DIR", env.get("HSA_DATA_DIR")), ("config file", read_config(config))):
        if value:
            path = Path(value).expanduser()
            if not path.is_dir():
                raise DataDirError(f"The data folder from {source} does not exist: {path}")
            return path.resolve()
    raise DataDirError(NOT_SET)


def data_dir_or_exit(cli=None):
    try:
        return data_dir(cli)
    except DataDirError as e:
        print(e, file=sys.stderr)
        raise SystemExit(2)


RECEIPT_TYPES = ("order", "bill", "receipt", "eob", "letter")
RECEIPT_NAME_RE = r"^\d{4}-\d{2}-\d{2}_(" + "|".join(RECEIPT_TYPES) + r")_"

APP_README = (
    "This folder holds the app's own files: orders, images, the product cache, backups, and logs.\n"
    "Nothing here needs your attention, and nothing here should be edited by hand.\n"
    "Your documents are in ../receipts, your reports in ../reports, and your choices in ../decisions.json.\n"
)


def year_paths(data, year):
    """Where each file of one year lives. A year uses the older flat layout only while its old data file exists
    and the new one does not (until tools/migrate_layout.py has run); everything else uses the simple layout."""
    data = Path(data)
    y = data / str(year)
    app = y / "_app"
    new = (app / "data.json").exists() or not (y / f"hsa_data_{year}.json").exists()
    return SimpleNamespace(
        year_dir=y,
        new_layout=new,
        receipts=y / "receipts",
        reports=y / "reports",
        app=app,
        data=app / "data.json" if new else y / f"hsa_data_{year}.json",
        decisions=y / "decisions.json" if new else y / f"hsa_decisions_{year}.json",
        cache=app / "product_cache.json" if new else y / f"asin_info_{year}.json",
        images=app / "images" if new else data / "images",
        backups=app / "backups" if new else y / "backups",
    )


def unidentified(receipts):
    """Files in receipts/ whose names do not say what they are (date_type_...)."""
    import re

    if not Path(receipts).is_dir():
        return []
    return sorted(f.name for f in Path(receipts).iterdir() if f.is_file() and not re.match(RECEIPT_NAME_RE, f.name))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Show or set the folder that holds your data (not the code folder).")
    ap.add_argument("--set", metavar="FOLDER", help="save FOLDER as your data folder (it is created if missing)")
    ap.add_argument("--show", action="store_true", help="print the data folder (the default action)")
    ap.add_argument("--suggest", action="store_true", help="print the suggested default folder")
    args = ap.parse_args()
    if args.set:
        Path(args.set).expanduser().mkdir(parents=True, exist_ok=True)
        write_config(args.set)
        print("Data folder saved:", data_dir())
    elif args.suggest:
        print(default_data_dir())
    else:
        print(data_dir_or_exit())
