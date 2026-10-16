"""Tests for organize_files.py using fake documents (no real data, no Amazon contact).

Run:  python tools/test_organize_files.py
"""

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_samples import html_to_pdf  # noqa: E402
from organize_files import main  # noqa: E402

DOCS = {
    "invoice (3).pdf": "<h2>Amazon.com Order Summary</h2><p>Order Placed: March 14, 2025</p><p>Order # 900-0000001-0000001</p><p>SAMPLE</p>",
    "download.pdf": "<h2>Sample ENT Clinic</h2><p>Patient: Alex Example</p><p>Statement date: 2025-06-09</p><p>Amount due: $10.00</p><p>SAMPLE</p>",
    "eob.pdf": "<h2>Example Health Plan</h2><p>Explanation of Benefits. This is not a bill.</p><p>2025-06-20</p><p>SAMPLE</p>",
    "letter.pdf": "<h2>Sample ENT Clinic</h2><p>Letter of medical necessity for a heated eye massager.</p><p>September 2, 2025</p><p>SAMPLE</p>",
    "pharmacy.pdf": "<h2>Example Pharmacy Store</h2><p>Receipt</p><p>2025-07-04</p><p>Subtotal $8.00</p><p>SAMPLE</p>",
    "mystery.pdf": "<h2>Some flyer</h2><p>2025-01-01</p><p>SAMPLE</p>",
    "december.pdf": "<h2>Sample ENT Clinic</h2><p>Patient: Alex Example</p><p>Statement date: 2024-12-20</p><p>Amount due: $5.00</p><p>SAMPLE</p>",
    "scan.pdf": "<html><body></body></html>",
}


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    base = tmp_path_factory.mktemp("docs")
    for name, html in DOCS.items():
        html_to_pdf(html, base / name)
    shutil.copyfile(base / "download.pdf", base / "copy of download.pdf")  # a second download of the same file
    (base / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    stamp = datetime(datetime.now().year, 5, 1).timestamp()
    for f in base.iterdir():
        os.utime(f, (stamp, stamp))
    return base


@pytest.fixture()
def inbox(made, tmp_path):
    inbox = tmp_path / "inbox"
    shutil.copytree(made, inbox)
    return inbox, tmp_path / "project"


def names(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def test_default_run_changes_nothing(inbox, capsys):
    folder, root = inbox
    root.mkdir()
    before = names(folder)
    assert main([str(folder), "--year", "2025"], root=root) == 0
    assert names(folder) == before and not any(root.iterdir())
    assert "plan only" in capsys.readouterr().out


def test_confirm_moves_files_into_receipts_named_date_type_source_detail(inbox):
    folder, root = inbox
    root.mkdir()
    main([str(folder), "--year", "2025", "--confirm"], root=root)
    got = names(root)
    assert "2025/receipts/2025-03-14_order_amazon_900-0000001-0000001.pdf" in got
    assert any(g.startswith("2025/receipts/2025-06-09_bill_Sample-ENT-Clinic_visit") for g in got)
    assert any(g.startswith("2025/receipts/2025-06-20_eob_Example-Health-Plan_statement") for g in got)
    assert any(g.startswith("2025/receipts/2025-09-02_letter_Sample-ENT-Clinic_LMN") for g in got)
    assert any(g.startswith("2025/receipts/2025-07-04_receipt_Example-Pharmacy-Store_purchase") for g in got)
    assert any(g.startswith("2024/receipts/2024-12-20_bill_") for g in got)  # the year comes from the document date
    assert all(g.split("/")[1] == "receipts" for g in got if not g.endswith(".json"))  # one flat folder, no sub-folders


def test_unidentified_files_keep_their_names(inbox, capsys):
    folder, root = inbox
    root.mkdir()
    main([str(folder), "--year", "2025", "--confirm"], root=root)
    got = names(root)
    this_year = str(datetime.now().year)
    assert "2025/receipts/mystery.pdf" in got  # a date is visible, so the document year decides the folder
    for original in ("scan.pdf", "photo.png"):  # no date can be read, so the download year is used
        assert f"{this_year}/receipts/{original}" in got
    assert "not identified" in capsys.readouterr().out


def test_duplicates_by_hash_stay_in_the_inbox(inbox):
    folder, root = inbox
    root.mkdir()
    main([str(folder), "--year", "2025", "--confirm"], root=root)
    assert "copy of download.pdf" in names(folder) or "download.pdf" in names(folder)
    assert sum(1 for g in names(root) if "_bill_Sample-ENT-Clinic_visit" in g and g.startswith("2025/")) == 1


def test_download_year_mismatch_is_flagged(inbox, capsys):
    folder, root = inbox
    root.mkdir()
    main([str(folder), "--year", "2025"], root=root)
    assert "differs from download year" in capsys.readouterr().out


def test_without_an_inbox_it_renames_what_is_already_in_receipts(tmp_path, made):
    receipts = tmp_path / "2025" / "receipts"
    receipts.mkdir(parents=True)
    shutil.copyfile(made / "download.pdf", receipts / "scan0001.pdf")
    shutil.copyfile(made / "mystery.pdf", receipts / "mystery.pdf")
    main(["--year", "2025", "--confirm"], root=tmp_path)
    got = sorted(p.name for p in receipts.iterdir())
    assert "2025-06-09_bill_Sample-ENT-Clinic_visit.pdf" in got and "mystery.pdf" in got and "scan0001.pdf" not in got
    main(["--year", "2025", "--confirm"], root=tmp_path)  # a second run finds nothing more to do
    assert sorted(p.name for p in receipts.iterdir()) == got


def test_undo_puts_everything_back_and_nothing_is_deleted(inbox):
    folder, root = inbox
    root.mkdir()
    before = names(folder)
    main([str(folder), "--year", "2025", "--confirm"], root=root)
    assert names(folder) != before
    main(["--undo"], root=root)
    assert names(folder) == before
    assert not [g for g in names(root) if g.endswith(".pdf")]


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "--tb=short", "-p", "no:cacheprovider", __file__]))
