"""Opens the review page with your data folder, served on this computer only.

The page lives in this code folder; your data lives elsewhere (see hsa_paths.py). This small
local server shows review.html and your data folder side by side, and nothing else: the rest of
the code folder and the internet cannot see your data.

  python tools/open_review.py                     # data folder from setup or HSA_DATA_DIR
  python tools/open_review.py --data-dir samples  # try the page on the fake sample data
"""

import argparse
import http.server
import json
import re
import sys
import webbrowser
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlsplit
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsa_paths import data_dir_or_exit  # noqa: E402

CODE_DIR = Path(__file__).resolve().parent.parent


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serves /review.html and the rules file from the code folder, /data/... from the data folder, and /status.json."""

    def __init__(self, *args, data_dir, **kwargs):
        self.data_dir = Path(data_dir).resolve()
        super().__init__(*args, **kwargs)

    def translate_path(self, path):
        clean = unquote(path.split("?", 1)[0].split("#", 1)[0])
        if clean in ("/", "/review.html"):
            return str(CODE_DIR / "review.html")
        if clean == "/skills/hsa-categorize/category_rules.js":  # the shared rules (part of the program, not your data)
            return str(CODE_DIR / "skills" / "hsa-categorize" / "category_rules.js")
        if clean.startswith("/data/"):
            target = (self.data_dir / clean[len("/data/"):].lstrip("/")).resolve()
            if target == self.data_dir or self.data_dir in target.parents:
                return str(target)
        return str(CODE_DIR / "__not_served__")  # anything else is a 404

    def _json(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlsplit(self.path).path == "/years.json":  # the year folders in the data folder, newest first
            years = sorted((d.name for d in self.data_dir.iterdir() if d.is_dir() and re.fullmatch(r"\d{4}", d.name)), reverse=True)
            return self._json({"years": years})
        if urlsplit(self.path).path == "/receipts.json":  # file names in <year>/receipts/ (the page links each order to its invoice)
            year = (parse_qs(urlsplit(self.path).query).get("year") or [""])[0]
            if not re.fullmatch(r"\d{4}", year):
                return self.send_error(400, "Bad year")
            folder = self.data_dir / year / "receipts"
            return self._json({"files": sorted(f.name for f in folder.iterdir() if f.is_file()) if folder.is_dir() else []})
        if urlsplit(self.path).path == "/status.json":  # the same checklist as `hsa.py status`
            import hsa

            year = (parse_qs(urlsplit(self.path).query).get("year") or [str(datetime.now().year)])[0]
            if not re.fullmatch(r"\d{4}", year):
                return self.send_error(400, "Bad year")
            return self._json(hsa.status_json(year, str(self.data_dir)))
        super().do_GET()

    def list_directory(self, path):
        self.send_error(404, "No listing")
        return None

    def log_message(self, *args):
        pass


def make_server(data_dir, port=8765):
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, data_dir=data_dir))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", help="your data folder (default: from setup or HSA_DATA_DIR)")
    ap.add_argument("--year", default=None, help="tax year to open (default: this year)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true", help="do not open a browser")
    args = ap.parse_args(argv)
    folder = data_dir_or_exit(args.data_dir)
    server = make_server(folder, args.port)
    url = f"http://127.0.0.1:{server.server_address[1]}/review.html" + (f"?year={args.year}" if args.year else "")
    print(f"Data folder: {folder}\nOpen {url}\nPress Ctrl+C to stop.")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
