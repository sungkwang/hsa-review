"""Writes skills/hsa-categorize/category_rules.js from category_rules.json (the JSON stays the source).

A page opened by double-click cannot read a JSON file next to it, but it can load a script, so the same
rules are carried in a .js file. tools/test_rules.py checks that the two never differ.

  python tools/make_rules_js.py          # rewrite the .js file
  python tools/make_rules_js.py --check  # exit 1 if the .js file is out of date
"""

import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "skills" / "hsa-categorize"
SOURCE = DIR / "category_rules.json"
TARGET = DIR / "category_rules.js"
HEADER = "// Generated from category_rules.json by tools/make_rules_js.py. Do not edit; change the JSON and run the tool.\n"


def build():
    rules = json.loads(SOURCE.read_text(encoding="utf-8"))
    return HEADER + "window.CATEGORY_RULES = " + json.dumps(rules, ensure_ascii=False, indent=1) + ";\n"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    text = build()
    if "--check" in argv:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        print("up to date" if current == text else "out of date: run python tools/make_rules_js.py")
        return 0 if current == text else 1
    TARGET.write_text(text, encoding="utf-8")
    print("wrote", TARGET.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
