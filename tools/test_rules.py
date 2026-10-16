"""The review page and the Python tools must give the same answers from the shared rules file.

Run:  python tools/test_rules.py
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

import testserver  # noqa: E402
from rules import RULES_PATH, Rules  # noqa: E402
from test_review_page import DATA, page  # noqa: E402,F401  (the page fixture starts the launcher on fake data)

ROOT = Path(__file__).resolve().parent.parent

# (title, marked by Amazon, fake product ID or "")
ITEMS = [
    ("Air Purifier for Home, Captures Pet Allergies", False, "BFAKE00001"),
    ("Digital Thermometer for Adults", False, "BFAKE00002"),  # the product page shows the badge
    ("Daily Multivitamin Gummies", False, "BFAKE00003"),  # Amazon path: Health & Household > Vitamins
    ("Resistance Bands Set", False, "BFAKE00004"),  # an Amazon path with no mapping: Other
    ("Kids Shampoo + Conditioner, Gentle", False, "BFAKE00005"),
    ("Anti-Dandruff Shampoo with 1% Ketoconazole", False, ""),
    ("Wireless Mouse - for Small Hands, Silent Clicks", False, ""),
    ("Upper Arm Blood Pressure Monitor, Large Cuff", False, ""),
    ("Knee Brace Support for Running", False, ""),
    ("USB Cable 6ft Braided Charger", False, ""),
    ("Dog Food, Adult, Chicken", False, ""),
    ("Heated Eye Massager", True, ""),
    ("Elbow Compression Sleeve with Gel Pads", False, ""),
    ("Tropical Fruit Gummies Candy 12 Pack", False, ""),
    ("Sensodyne Toothpaste for Sensitive Teeth", False, ""),
]


def test_rules_file_has_a_version():
    assert json.loads(RULES_PATH.read_text(encoding="utf-8"))["version"] == Rules().version >= 1


def test_the_script_the_page_loads_from_disk_has_the_same_rules_and_version_as_the_json():
    import make_rules_js

    js = make_rules_js.TARGET.read_text(encoding="utf-8")
    assert js == make_rules_js.build(), "category_rules.js is out of date: run python tools/make_rules_js.py"
    body = js.split("window.CATEGORY_RULES = ", 1)[1].rstrip().rstrip(";")
    from_js = json.loads(body)
    from_json = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    assert from_js == from_json and from_js["version"] == from_json["version"]


def test_page_and_python_tools_give_the_same_likelihood_and_category(page):  # noqa: F811
    rules = Rules()
    info = DATA["ASIN_INFO"]
    for title, marked, asin in ITEMS:
        js_like, js_cat = page.evaluate("([t, m, a]) => [likelihood(t, m, a), catOf(t, a)]", [title, marked, asin])
        entry = info.get(asin) if asin else None
        py_like = rules.likelihood(title, marked, entry)
        py_cat = rules.cat_of(title, entry)
        assert js_like == py_like, (title, js_like, py_like)
        assert (js_cat["name"], js_cat["why"], js_cat["icon"]) == (py_cat["name"], py_cat["why"], py_cat["icon"]), (title, js_cat, py_cat)


def test_the_rules_say_what_the_agreed_decisions_say():
    r = Rules()
    for title, expected in [
        ("Daily Multivitamin Gummies", "Unlikely"),
        ("Kids Shampoo + Conditioner, Gentle", "Unlikely"),
        ("Anti-Dandruff Shampoo with 1% Ketoconazole", "Likely"),
        ("Upper Arm Blood Pressure Monitor, Large Cuff", "Likely"),  # Electronics, raised by a medical word
        ("USB Cable 6ft Braided Charger", "Highly unlikely"),
    ]:
        assert r.likelihood(title)["label"] == expected, title
    vitamins = {"path": ["Health & Household", "Vitamins, Minerals & Supplements", "Multivitamins"], "fsa": False}
    assert r.cat_of("x", vitamins)["name"] == "Vitamins and supplements"
    assert r.likelihood("x", False, vitamins)["label"] == "Unlikely"
    assert r.likelihood("x", False, {**vitamins, "fsa": True})["label"] == "Highly likely"  # the badge wins
    assert r.cat_of("x", {"path": ["Automotive", "Car Care"]})["why"].startswith("Other (Amazon:")


def _serve(tmp_path):
    server, port = testserver.start(lambda p: [sys.executable, str(ROOT / "tools" / "open_review.py"), "--data-dir", str(tmp_path), "--port", str(p), "--no-open"])
    return server, f"http://127.0.0.1:{port}/review.html?year=2099"


def test_a_broken_data_file_shows_an_error_that_names_it(tmp_path):
    pw = pytest.importorskip("playwright.sync_api")
    (tmp_path / "2099").mkdir()
    (tmp_path / "2099" / "hsa_data_2099.json").write_text("{ this is not json", encoding="utf-8")
    server, url = _serve(tmp_path)
    try:
        with pw.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page()
            pg.goto(url, wait_until="load")
            pg.wait_for_selector(".load-error", timeout=10000)
            text = pg.locator(".load-error").inner_text()
            browser.close()
        assert "2099/hsa_data_2099.json" in text and "not valid JSON" in text
    finally:
        server.terminate()


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "--tb=short", "-p", "no:cacheprovider", __file__]))
