#!/usr/bin/env python3
"""
Scan the files this project would publish for personal data.

Uses `git ls-files --cached --others --exclude-standard`, so ignored folders
(year data, images, .agent) are not scanned. Outside a git repo, every file is
scanned. Checks file and folder names, Amazon order numbers, and any extra terms
(names, street address) listed in the file named by HSA_PERSONAL_TERMS, one per
line. That file stays on your computer; never add it to the repository.

Run from the project folder:  python tools/check_personal_data.py
Exit code 1 means something personal was found.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ORDER_RE = re.compile(r"\b\d{3}-\d{7}-\d{7}\b")
# Obviously invented order numbers: a 900- prefix, a middle part of one repeated digit (0000000, 2222222), or 1234567
FAKE_ORDER_RE = re.compile(r"(?:900-\d{7}-\d{7}|\d{3}-(?:(\d)\1{6}|1234567)-\d{7})")
# Product IDs (ASINs) the same way: outside samples/, only invented ones may appear (BFAKE##### never matches the pattern below)
ASIN_LIKE_RE = re.compile(r"\bB0[0-9A-Z]{8}\b")
FAKE_ASIN_RE = re.compile(r"B0{9}|B012345678")
LICENSE_RE = re.compile(r"^LICENSE(\.md|\.txt)?$", re.I)  # a license names its copyright holder on purpose
BAD_NAME_RES = [
    re.compile(r"^\d{4}$"),                       # year folders such as 2026/
    re.compile(r"^hsa_(data|decisions)_\d{4}\.(js|json)$"),
    re.compile(r"^amazon_hsa_decisions_\d{4}\.csv$"),
    re.compile(r"\.(pdf|csv|jpg|jpeg|png|heic)$", re.I),
    re.compile(r"^cookies\.json$"),
    re.compile(r"^\.mcp\.json$"),
    re.compile(r"^(images|\.agent|\.venv|__pycache__|\.git)$"),
]
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {".md", ".py", ".js", ".html", ".json", ".txt", ".toml", ".cfg", ".example", ""}


def personal_terms():
    path = os.environ.get("HSA_PERSONAL_TERMS")
    if not path or not Path(path).is_file():
        return []
    return [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def project_files(root):
    """Files git would publish; every file under root when there is no git repo."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True,
        ).stdout
        return [root / p for p in out.splitlines() if p and (root / p).is_file()]
    except (OSError, subprocess.CalledProcessError):
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            files += [Path(dirpath) / f for f in filenames]
        return files


ASIN_RE = re.compile(r"\bB[0-9A-Z]{9}\b")
SAMPLE_BINARY = {".pdf"}
SAMPLE_IMAGES = {".png", ".jpg", ".jpeg"}


def data_folders(root):
    """Folders that may hold real data: any year folders left in the code folder, and the data folder."""
    found = [Path(root)]
    try:
        from hsa_paths import DataDirError, data_dir

        found.append(data_dir())
    except (ImportError, DataDirError):
        pass
    return found


def repo_data_problems(root):
    """User data must not be inside the code folder at all, ignored or not."""
    root = Path(root)
    problems = []
    for child in root.iterdir() if root.is_dir() else []:
        if child.is_dir() and re.fullmatch(r"\d{4}", child.name):
            problems.append(f"{child.name}/: a year folder inside the code folder; move it to your data folder")
        elif child.is_dir() and child.name in {"images", "organize_log"}:
            problems.append(f"{child.name}/: user data inside the code folder; move it to your data folder")
        elif child.is_file() and re.fullmatch(r"hsa_(data|decisions)_\d{4}\.(js|json)|amazon_.*\.csv", child.name):
            problems.append(f"{child.name}: user data inside the code folder; move it to your data folder")
    return problems


def private_values(root):
    """Real order numbers and product IDs from the private year folders (never printed)."""
    orders, asins = set(), set()
    files = [f for base in data_folders(root) for f in base.glob("[0-9][0-9][0-9][0-9]/*")]
    for f in files:
        if f.suffix.lower() in {".js", ".json", ".csv"}:
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            orders |= set(ORDER_RE.findall(text))
            asins |= set(ASIN_RE.findall(text))
    return orders, asins


def pdf_text_and_metadata(path):
    from pypdf import PdfReader

    reader = PdfReader(path)
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    meta = " ".join(str(v) for v in (reader.metadata or {}).values() if str(v).strip())
    return text, meta


def check_sample(path, rel, root, terms, orders, asins):
    """A file in samples/ may be a PDF or image, but its contents must be fake and marked SAMPLE."""
    problems = []
    suffix = path.suffix.lower()
    text, meta = "", ""
    if suffix in SAMPLE_BINARY:
        try:
            text, meta = pdf_text_and_metadata(path)
        except ImportError:
            return [f"{rel}: pypdf is not installed, so this sample PDF was not checked"]
        except Exception:
            return [f"{rel}: the sample PDF could not be read"]
        if meta.strip():
            problems.append(f"{rel}: PDF metadata is not empty")
    elif suffix in SAMPLE_IMAGES:
        if "sample" not in path.name.lower():
            problems.append(f"{rel}: image name must contain 'sample'")
        return problems
    elif suffix in TEXT_SUFFIXES | {".csv"}:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return [f"{rel}: could not be read"]
    else:
        return [f"{rel}: file type not allowed in samples/"]
    if "sample" not in text.lower():
        problems.append(f"{rel}: no visible SAMPLE marker")
    for number in ORDER_RE.findall(text):
        if number in orders:
            problems.append(f"{rel}: a real order number")
        elif not number.startswith("900-"):
            problems.append(f"{rel}: order number {number} does not start with 900-")
    problems += [f"{rel}: a real product ID" for a in set(ASIN_RE.findall(text)) if a in asins]
    problems += [f"{rel}: contains a personal term" for t in terms if t in text or t in meta]
    return problems


def scan(root):
    """Return a list of problem strings. Empty means clean."""
    root = Path(root)
    terms = personal_terms()
    problems = []
    orders, asins = private_values(root)
    problems += repo_data_problems(root)
    for path in project_files(root):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] == "samples":
            problems += check_sample(path, rel, root, terms, orders, asins)
            continue
        if any(r.search(part) for part in rel.parts for r in BAD_NAME_RES):
            problems.append(f"{rel}: personal file or folder name")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for m in ORDER_RE.finditer(text):
            if not FAKE_ORDER_RE.fullmatch(m.group(0)):  # invented numbers can never match a real order
                problems.append(f"{rel}: Amazon order number {m.group(0)}")
        for m in ASIN_LIKE_RE.finditer(text):
            if not FAKE_ASIN_RE.fullmatch(m.group(0)):  # a real-looking product ID can show what was bought; use BFAKE#####
                problems.append(f"{rel}: Amazon product ID {m.group(0)} (use an invented one such as BFAKE00001)")
        for term in terms:
            if term in text and not LICENSE_RE.match(path.name):
                problems.append(f"{rel}: contains a personal term")
    return problems


def main():
    root = Path(__file__).resolve().parent.parent
    problems = scan(root)
    if problems:
        print("Personal data found:")
        for p in problems:
            print("  " + p)
        return 1
    print("Clean: no personal file names, order numbers, or listed terms.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
