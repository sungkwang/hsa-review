"""Tests for hsa.py status and setup, and for the page's first-run checklist. No Amazon contact.

Run:  python tools/test_hsa_status.py
"""

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hsa  # noqa: E402
import testserver  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def by_name(items, start):
    return next(i for i in items if i["name"].startswith(start))


def test_missing_data_folder_names_the_next_step(tmp_path, monkeypatch):
    monkeypatch.delenv("HSA_DATA_DIR", raising=False)
    monkeypatch.setattr("hsa_paths.CONFIG", tmp_path / "none.json")
    monkeypatch.setattr("hsa.data_dir", lambda cli=None: (_ for _ in ()).throw(hsa.DataDirError("No data folder set. Run setup (or pass --data-dir).")))
    step = by_name(hsa.steps("2099"), "Data folder")
    assert not step["ok"] and "setup" in step["next"]


def test_invoices_lists_claimable_orders_that_have_no_invoice_file(tmp_path):
    app = tmp_path / "2099" / "_app"
    (tmp_path / "2099" / "receipts").mkdir(parents=True)
    app.mkdir(parents=True)
    orders = [
        {"id": "111-0000000-0000001", "date": "January 5, 2099", "items": [{"marked": True}]},   # marked by Amazon, invoice saved
        {"id": "111-0000000-0000002", "date": "January 6, 2099", "items": [{"marked": False}]},  # you set it to Eligible
        {"id": "111-0000000-0000003", "date": "January 7, 2099", "items": [{"marked": False}]},  # not decided: no invoice wanted
        {"id": "111-0000000-0000004", "date": "January 8, 2099", "items": [{"marked": True}]},   # you set it to Not eligible
    ]
    (app / "data.json").write_text(json.dumps({"ORDERS": orders, "ALL_ORDERS": [{"id": "111-0000000-0000005", "date": "January 9, 2099", "items": ["x"]}]}), encoding="utf-8")
    (tmp_path / "2099" / "decisions.json").write_text(json.dumps({
        "111-0000000-0000002|0": {"status": "Eligible"},
        "111-0000000-0000004|0": {"status": "Not eligible"},
        "ALL|111-0000000-0000005": {"status": "Need LMN"},
    }), encoding="utf-8")
    (tmp_path / "2099" / "receipts" / "2099-01-05_order_amazon_111-0000000-0000001.pdf").write_bytes(b"%PDF")
    assert hsa.missing_invoices("2099", str(tmp_path)) == ["111-0000000-0000002", "111-0000000-0000005"]


def test_year_with_data_and_decisions_is_checked_off(tmp_path):
    year = tmp_path / "2099"
    year.mkdir()
    (year / "hsa_data_2099.json").write_text(json.dumps({"ORDERS": [{"id": "x"}], "ALL_ORDERS": [], "MEDICAL": [{"id": "m"}]}), encoding="utf-8")
    (year / "hsa_decisions_2099.json").write_text(json.dumps({"a|0": {"status": "Eligible"}, "__taxRate": 7}), encoding="utf-8")
    items = hsa.steps("2099", str(tmp_path))
    assert by_name(items, "Data folder")["ok"]
    assert by_name(items, "2099 folder")["ok"]
    assert by_name(items, "2099 orders")["detail"] == "1 orders"
    assert by_name(items, "Medical")["ok"]
    assert by_name(items, "Reviewed")["detail"] == "1 decisions saved"  # the __taxRate setting is not a decision


def test_documents_without_a_type_in_their_name_are_listed_as_not_identified(tmp_path):
    app = tmp_path / "2099" / "_app"
    app.mkdir(parents=True)
    (app / "data.json").write_text("{}", encoding="utf-8")
    receipts = tmp_path / "2099" / "receipts"
    receipts.mkdir()
    (receipts / "2099-01-02_bill_Sample-Clinic_visit.pdf").write_bytes(b"x")
    (receipts / "scan0001.pdf").write_bytes(b"x")
    step = by_name(hsa.steps("2099", str(tmp_path)), "Documents named")
    assert not step["ok"] and "1 not identified: scan0001.pdf" in step["detail"] and "organize_files.py" in step["next"]


def test_render_marks_only_the_first_unchecked_step_as_next():
    items = [hsa._step("A", True, "ok"), hsa._step("B", False, "missing", "do B"), hsa._step("C", False, "missing", "do C")]
    text = hsa.render(items)
    assert "[x] A" in text and text.count("<- Next:") == 1 and "do B" in text and "do C" not in text


def test_status_json_has_the_next_step_and_done_flag(tmp_path):
    result = hsa.status_json("2099", str(tmp_path))
    assert result["done"] is False and result["next"] and result["steps"]


def test_setup_creates_the_year_folder_from_the_templates(tmp_path, monkeypatch):
    monkeypatch.setattr(hsa, "steps", lambda year, cli=None: [hsa._step("Python 3.11 or newer", True, "ok"), hsa._step("Chrome or Edge", True, "ok"), hsa._step("Amazon reader installed", True, "ok")])
    lines = []
    assert hsa.setup("2099", str(tmp_path), say=lines.append) == 0
    year = tmp_path / "2099"
    assert (year / "_app" / "data.json").exists() and (year / "_app" / "README.txt").exists()
    assert (year / "receipts").is_dir() and (year / "reports").is_dir() and (year / "_app" / "images").is_dir()
    assert json.loads((year / "decisions.json").read_text(encoding="utf-8")) == {}
    assert sorted(p.name for p in year.iterdir()) == ["_app", "decisions.json", "receipts", "reports"]  # nothing else


def test_setup_stops_with_next_when_a_prerequisite_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(hsa, "steps", lambda year, cli=None: [hsa._step("Python 3.11 or newer", True, "ok"), hsa._step("Chrome or Edge", False, "not found", "Install Chrome or Edge, then run this again.")])
    lines = []
    assert hsa.setup("2099", str(tmp_path), say=lines.append) == 1
    assert any(line.startswith("Next: Install Chrome or Edge") for line in lines)
    assert not (tmp_path / "2099").exists()  # nothing is created until the prerequisites pass


def test_shortcut_runs_open_for_the_current_year_and_keeps_the_window_open_on_failure(tmp_path):
    path = hsa.make_shortcut(tmp_path, python="C:/Py/python.exe")
    if path is None:  # Linux has no desktop shortcut here
        pytest.skip("no shortcut on this system")
    text = path.read_text(encoding="utf-8")
    assert "hsa.py" in text and "open" in text and "--year" not in text  # the year is worked out each time it runs
    assert "Next:" in text and ("pause" in text or "read -p" in text)  # stays open with a next step when it fails


def test_setup_offers_the_shortcut_as_its_last_step(tmp_path, monkeypatch):
    monkeypatch.setattr(hsa, "steps", lambda year, cli=None: [hsa._step("Python 3.11 or newer", True, "ok"), hsa._step("Chrome or Edge", True, "ok"), hsa._step("Amazon reader installed", True, "ok")])
    desk = tmp_path / "Desktop"
    desk.mkdir()
    questions = []
    hsa.setup("2099", str(tmp_path / "data"), ask=lambda q: questions.append(q) or "y", say=lambda *_: None, desktop=desk)
    assert any("desktop shortcut" in q for q in questions)
    assert list(desk.iterdir()) or sys.platform not in ("win32", "darwin")


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_page_shows_the_checklist_when_the_year_has_no_data(tmp_path):
    pw = pytest.importorskip("playwright.sync_api")
    server, port = testserver.start(lambda p: [sys.executable, str(ROOT / "tools" / "open_review.py"), "--data-dir", str(tmp_path), "--port", str(p), "--no-open"])
    url = f"http://127.0.0.1:{port}/review.html?year=2099"
    try:
        with pw.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url, wait_until="load")
            page.wait_for_selector(".firstrun .next", timeout=10000)
            text = page.locator(".firstrun").inner_text()
            browser.close()
        assert errors == []
        assert "No 2099 data yet" in text and "Next:" in text
    finally:
        server.terminate()


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "--tb=short", "-p", "no:cacheprovider", __file__]))


def test_invoices_lists_claimable_orders_with_no_invoice_file(tmp_path):
    year = tmp_path / "2099"
    (year / "_app").mkdir(parents=True)
    (year / "receipts").mkdir()
    orders = [{"id": "A-1", "items": [{"marked": True}]}, {"id": "B-2", "items": [{"marked": False}]},
              {"id": "C-3", "items": [{"marked": False}]}, {"id": "D-4", "items": [{"marked": True}]}]
    (year / "_app" / "data.json").write_text(json.dumps({"ORDERS": orders, "ALL_ORDERS": [{"id": "E-5"}, {"id": "F-6"}]}), encoding="utf-8")
    (year / "decisions.json").write_text(json.dumps({"B-2|0": {"status": "Need LMN"}, "D-4|0": {"status": "Not eligible"}, "ALL|E-5": {"status": "Eligible"}}), encoding="utf-8")
    (year / "receipts" / "2099-01-01_order_amazon_A-1.pdf").write_bytes(b"%PDF")
    # A-1 has its file; B-2 (marked by you as Need LMN) and E-5 (whole order, Eligible) do not; C-3 undecided, D-4 not eligible, F-6 undecided
    assert hsa.missing_invoices("2099", str(tmp_path)) == ["B-2", "E-5"]
