"""HSA review: where you are, and what to do next.

  python tools/hsa.py status [--year 2026] [--data-dir PATH] [--json]
  python tools/hsa.py setup  [--year 2026] [--data-dir PATH]    # one step at a time, checks each
  python tools/hsa.py open   [--year 2026] [--data-dir PATH]    # same as tools/open_review.py
  python tools/hsa.py shortcut                                  # a double-click shortcut on the desktop

`status` inspects what is already done and names the next step. Every route (an agent, a terminal, the
review page) uses the same checklist, so the procedure is the same for everyone. Each failure ends with
"Next:" and one action. Nothing here contacts Amazon.
"""

import argparse
import importlib.util
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsa_paths import APP_README, CONFIG, DataDirError, data_dir, default_data_dir, unidentified, write_config, year_paths  # noqa: E402

CODE_DIR = Path(__file__).resolve().parent.parent
SIGN_IN_FILE = Path.home() / ".amazon-orders-mcp" / "last_sign_in.txt"
BROWSER_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app",
    "/Applications/Microsoft Edge.app",
]


def _step(name, ok, detail, next_action=""):
    return {"name": name, "ok": bool(ok), "detail": detail, "next": "" if ok else next_action}


def _browser():
    for exe in ("google-chrome", "chrome", "chromium", "msedge", "microsoft-edge"):
        if shutil.which(exe):
            return True
    return any(Path(p).exists() for p in BROWSER_PATHS)


def _load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def steps(year, cli_data_dir=None):
    out = []
    py_ok = sys.version_info >= (3, 11)
    out.append(_step("Python 3.11 or newer", py_ok, f"found {sys.version_info.major}.{sys.version_info.minor}", "Install Python 3.11 or 3.12, then run this again."))
    out.append(_step("Chrome or Edge", _browser(), "found" if _browser() else "not found", "Install Chrome or Edge, then run this again. The review page needs one of them."))
    mcp = importlib.util.find_spec("amazon_orders_mcp") is not None
    out.append(_step("Amazon reader installed", mcp, "amazon_orders_mcp is installed" if mcp else "not installed",
                     "From the repository folder run: pip install -e mcp/amazon-orders  and  python -m playwright install chromium"))
    try:
        folder = data_dir(cli_data_dir)
        out.append(_step("Data folder", True, str(folder)))
    except DataDirError as e:
        folder = None
        out.append(_step("Data folder", False, str(e), f"Run: python tools/hsa.py setup   (suggested folder: {default_data_dir()})"))
    paths = year_paths(folder, year) if folder else None
    data = _load_json(paths.data) if paths else None
    out.append(_step(f"{year} folder and data file", data is not None, "found" if data is not None else "missing",
                     f"Run: python tools/hsa.py setup --year {year}   (it creates the folder from the templates)"))
    if paths and paths.new_layout is False and data is not None:
        out.append(_step("Simple folder layout", False, "the older layout is still in use",
                         "Run: python tools/migrate_layout.py   (it prints the plan first; add --confirm to back up and move)"))
    try:
        minutes = (3600 - (time.time() - float(SIGN_IN_FILE.read_text()))) / 60
    except (OSError, ValueError):
        minutes = None
    signed = minutes is not None and minutes > 0
    detail = ("not recorded" if minutes is None else (f"{minutes:.0f} min left in the sign-in hour" if signed else "the last sign-in is over an hour old"))
    out.append(_step("Amazon sign-in (order pages need one from the last hour)", signed, detail,
                     "Ask your agent to run the refresh_session tool, or run python cookie_capture.py in the Amazon reader folder; sign in with 'Keep me signed in' ticked."))
    n_orders = len((data or {}).get("ORDERS", [])) + len((data or {}).get("ALL_ORDERS", []))
    out.append(_step(f"{year} orders pulled", n_orders > 0, f"{n_orders} orders" if n_orders else "none yet",
                     f'Ask your agent: "Pull my {year} Amazon orders" (it shows the page count and time and asks first).'))
    n_med = len((data or {}).get("MEDICAL", []))
    out.append(_step("Medical receipts added", n_med > 0, f"{n_med} entries" if n_med else "none yet (optional)",
                     f"Put bills in the {year}/receipts folder, or run: python tools/organize_files.py <your Downloads folder> --year {year}"))
    unnamed = unidentified(paths.receipts) if paths and paths.new_layout else []
    out.append(_step("Documents named by type", not unnamed, "all named" if not unnamed else f"{len(unnamed)} not identified: " + ", ".join(unnamed[:3]) + (" ..." if len(unnamed) > 3 else ""),
                     f"Run: python tools/organize_files.py --year {year}   (it prints a plan first); rename what it cannot read, e.g. 2026-08-14_receipt_pharmacy.png"))
    decisions = _load_json(paths.decisions) if paths else None
    n_dec = len([k for k in (decisions or {}) if not k.startswith("__")])
    out.append(_step("Reviewed in the page", n_dec > 0, f"{n_dec} decisions saved" if n_dec else "none yet",
                     "Double-click review.html in the code folder (or the HSA Review shortcut), choose your data folder once, set statuses, and click Save."))
    return out


def render(items):
    first = next((i for i in items if not i["ok"]), None)
    lines = []
    for i in items:
        mark = "[x]" if i["ok"] else "[ ]"
        tail = f"   <- Next: {i['next']}" if i is first and i["next"] else ""
        lines.append(f"{mark} {i['name']}: {i['detail']}{tail}")
    return "\n".join(lines)


def desktop_dir():
    return Path(os.environ.get("USERPROFILE") or Path.home()) / "Desktop"


def make_shortcut(desktop=None, python=None):
    """Write a double-click file that opens the review page for the current year. Returns its path, or None."""
    desktop = Path(desktop) if desktop else desktop_dir()
    if not desktop.is_dir():
        return None
    py = python or sys.executable
    if os.name == "nt":
        path = desktop / "HSA Review.bat"
        with open(path, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(
                "@echo off\n"
                "title HSA Review\n"
                f'cd /d "{CODE_DIR}"\n'
                f'set "PY={py}"\n'
                'if not exist "%PY%" set "PY=python"\n'
                "echo HSA Review. Keep this window open while you use the page. Close it to stop.\n"
                '"%PY%" tools\\hsa.py open\n'
                "if errorlevel 1 (\n"
                "  echo.\n"
                "  echo Something went wrong.\n"
                f'  echo Next: open a terminal in "{CODE_DIR}" and run: python tools\\hsa.py status\n'
                "  pause\n"
                ")\n",
            )
        return path
    if sys.platform == "darwin":
        path = desktop / "HSA Review.command"
        path.write_text(
            "#!/bin/bash\n"
            f'cd "{CODE_DIR}"\n'
            "echo 'HSA Review. Keep this window open while you use the page. Close it to stop.'\n"
            f'"{py}" tools/hsa.py open || {{ echo; echo "Something went wrong."; echo "Next: run: python3 tools/hsa.py status"; read -p "Press Enter to close"; }}\n',
            encoding="utf-8",
        )
        path.chmod(0o755)
        return path
    return None


def setup(year, cli_data_dir=None, ask=input, say=print, desktop=None, offer_shortcut=True):
    """Walk the steps one at a time. Each one is checked; a failure stops with a plain 'Next:' message."""
    items = steps(year, cli_data_dir)
    for i in items[:3]:
        say(f"{'[x]' if i['ok'] else '[ ]'} {i['name']}: {i['detail']}")
        if not i["ok"]:
            say(f"Next: {i['next']}")
            return 1
    try:
        folder = data_dir(cli_data_dir)
    except DataDirError:
        suggestion = default_data_dir()
        answer = cli_data_dir or ask(f"Where should your data live (outside this code folder)? [{suggestion}] ").strip() or str(suggestion)
        folder = Path(answer).expanduser()
        if CODE_DIR in [folder.resolve(), *folder.resolve().parents]:
            say("Next: choose a folder outside the code folder, then run setup again.")
            return 1
        folder.mkdir(parents=True, exist_ok=True)
        write_config(folder)
        say(f"[x] Data folder saved: {folder}")
    paths = year_paths(folder, year)
    if paths.new_layout:
        for d in (paths.receipts, paths.reports, paths.app, paths.images):
            d.mkdir(parents=True, exist_ok=True)
        if not (paths.app / "README.txt").exists():
            (paths.app / "README.txt").write_text(APP_README, encoding="utf-8")
        for template, target in (("hsa_data_example.json", paths.data), ("hsa_decisions_example.json", paths.decisions)):
            if not target.exists():
                shutil.copyfile(CODE_DIR / "templates" / template, target)
                say(f"[x] Created {target.relative_to(folder).as_posix()} from the template")
    say("")
    say(render(steps(year, cli_data_dir)))
    if offer_shortcut and (ask is not input or sys.stdin.isatty()):
        if ask("Create a desktop shortcut (double-click to open the page)? (y/n) ").strip().lower().startswith("y"):
            path = make_shortcut(desktop)
            say(f"[x] Shortcut created: {path}" if path else "Next: no desktop folder was found, so no shortcut was made. You can open the page with: python tools/hsa.py open")
    return 0


def status_json(year, cli_data_dir=None):
    items = steps(year, cli_data_dir)
    first = next((i for i in items if not i["ok"]), None)
    return {"year": year, "steps": items, "next": first["next"] if first else "", "done": first is None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "setup", "open", "shortcut"])
    ap.add_argument("--year", default=str(datetime.now().year))
    ap.add_argument("--data-dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.command == "open":
        import open_review

        return open_review.main(["--year", args.year] + (["--data-dir", args.data_dir] if args.data_dir else []))
    if args.command == "shortcut":
        path = make_shortcut()
        print(f"Shortcut created: {path}" if path else "Next: no desktop folder was found. Open the page with: python tools/hsa.py open")
        return 0 if path else 1
    if args.command == "setup":
        return setup(args.year, args.data_dir)
    if args.json:
        print(json.dumps(status_json(args.year, args.data_dir), indent=1))
    else:
        print(render(steps(args.year, args.data_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
