"""Checks review.html in headless Chromium with a fake year. No Amazon contact.

The fake year has an item in every section: a confirmed item, a Doctor's note / LMN
item, an unmarked item, a medical receipt, a whole-order item, and a skipped order.
Run after every change to the page:  python tools/test_review_page.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import testserver  # noqa: E402

playwright_sync = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parent.parent

DATA = {
    "DATA_AS_OF": {"pulled": "2099-01-01", "through": "2099-01-01", "yearComplete": False},
    "YEAR_CONFIG": {"priorUnreimbursed": 0, "threshold": 0},
    "ORDERS": [
        {"date": "January 5, 2099", "id": "TEST-ORDER-1", "total": 10, "items": [
            {"t": "Confirmed Bandages", "p": 10, "seller": "Seller A", "marked": True, "img": ""}]},
        {"date": "January 6, 2099", "id": "TEST-ORDER-2", "total": 20, "items": [
            {"t": "Eye Massager", "p": 20, "seller": "Seller B", "marked": True, "img": ""}]},
        {"date": "January 7, 2099", "id": "TEST-ORDER-3", "total": 5, "items": [
            {"t": "Plain Cable", "p": 5, "seller": "Seller C", "marked": False, "img": ""}]},
    ],
    "MEDICAL": [{"id": "MED|1", "icon": "", "thumb": "", "who": "Test Person", "provider": "Test Clinic", "date": "2099-02-01", "amount": 50, "src": "bill.pdf", "note": ""}],
    "ALL_ORDERS": [{"date": "January 9, 2099", "id": "TEST-ORDER-9", "total": "$7.00", "items": ["Pill Organizer"], "pdf": False, "img": "", "suggest": {"level": "Likely", "why": "Test: listed as eligible"}}],
    "SKIPPED_ORDERS": [{"date": "January 10, 2099", "id": "TEST-ORDER-10", "reason": "Returned: refunded", "items": ["Returned Thing"]}],
    "ASIN_INFO": {
        "BFAKE00001": {"path": ["Home & Kitchen", "Heating, Cooling & Air Quality", "Air Purifiers"], "fsa": False, "read": "2099-01-01"},
        "BFAKE00002": {"path": ["Health & Household", "Health Care", "First Aid"], "fsa": True, "read": "2099-01-01"},
        "BFAKE00003": {"path": ["Health & Household", "Vitamins, Minerals & Supplements", "Multivitamins"], "fsa": False, "read": "2099-01-01"},
        "BFAKE00004": {"path": ["Sports & Outdoors", "Exercise & Fitness"], "fsa": False, "read": "2099-01-01"},
        "BFAKE00005": {"path": ["Beauty & Personal Care", "Hair Care"], "fsa": False, "read": "2099-01-01"},
    },
}
DECISIONS = {"TEST-ORDER-2|0": {"status": "Need LMN"}, "__taxRate": 0}


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture()
def page(tmp_path):
    year = tmp_path / "2099"
    (year / "_app").mkdir(parents=True)
    (year / "_app" / "data.json").write_text(json.dumps(DATA), encoding="utf-8")
    (year / "decisions.json").write_text(json.dumps(DECISIONS), encoding="utf-8")
    # The launcher runs as its own process, the way users run it (the page reads its data through it)
    server, port = testserver.start(lambda p: [sys.executable, str(ROOT / "tools" / "open_review.py"), "--data-dir", str(tmp_path), "--port", str(p), "--no-open"])
    url = f"http://127.0.0.1:{port}/review.html?year=2099"
    try:
        with playwright_sync.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            pg = browser.new_page(viewport={"width": 1100, "height": 900})
            pg.errors = []
            pg.on("pageerror", lambda e: pg.errors.append(str(e)))
            pending = {}
            pg.on("request", lambda r: pending.__setitem__(r.url, r.method))
            pg.on("requestfinished", lambda r: pending.pop(r.url, None))
            pg.on("requestfailed", lambda r: pending.pop(r.url, None))
            try:
                pg.goto(url, wait_until="load", timeout=15000)
            except playwright_sync.TimeoutError:  # a stalled load: say which requests never finished, then try once more
                stuck = [u.replace(f"http://127.0.0.1:{port}", "") for u in pending]
                print("STALLED LOAD, unfinished requests:", stuck, "| server alive:", server.poll() is None)
                pg.goto(url, wait_until="load", timeout=30000)
            pg.wait_for_selector("#loading", state="detached", timeout=15000)  # data and rules have loaded and the page code has run
            yield pg
            browser.close()
    finally:
        server.terminate()


def test_loads_without_errors(page):
    assert page.errors == []


def test_every_section_has_its_item(page):
    assert page.locator("#lmn .order").count() == 1          # Doctor's note / LMN
    assert page.locator("#medical .order").count() == 1       # medical receipt
    assert page.locator("#list .order").count() == 1          # confirmed (marked, eligible)
    assert page.locator("#all .order").count() == 2           # unconfirmed: unmarked item + whole order
    assert page.locator("#skipped .skip-row").count() == 1    # not counted


def test_totals_leave_out_doctors_note_items(page):
    eligible = page.locator(".eq-g").first.inner_text()
    assert eligible == "$60.00"  # 10 confirmed + 50 medical; the 20 LMN item is excluded


def test_amount_edit_marks_edited_and_updates_totals(page):
    box = page.locator("#list input.ovr-total").first
    marker = page.locator("#list .edited").first
    assert marker.evaluate("e => getComputedStyle(e).visibility") == "hidden"
    box.fill("9.50")
    box.dispatch_event("change")
    page.wait_for_timeout(200)
    assert page.locator(".eq-g").first.inner_text() == "$59.50"
    assert page.locator("#list .edited").first.evaluate("e => getComputedStyle(e).visibility") == "visible"


def test_reset_space_is_reserved_when_hidden(page):
    reset = page.locator("#list .ovr-reset").first
    assert reset.evaluate("e => getComputedStyle(e).display") != "none"
    assert reset.bounding_box()["width"] > 0


def test_every_row_has_one_reimbursed_control_on_the_top_line(page):
    # header (single-item orders) or name line; never the control row below
    assert page.locator("#list .order-head .reimb-box").count() == 1
    assert page.locator("#list .decide .reimb-box").count() == 0
    assert page.locator("#medical .order-head .reimb-box").count() == 1


def test_text_is_at_least_14px(page):
    small = page.evaluate("""() => [...document.querySelectorAll('.muted, .meta, .sub, .badge, .cat, .reimb-label')]
        .filter(e => e.offsetParent !== null && parseFloat(getComputedStyle(e).fontSize) < 14).length""")
    assert small == 0


def test_personal_care_is_unlikely_and_drug_ingredients_are_likely(page):
    kids = page.evaluate("() => likelihood('Kids Shampoo + Conditioner + Body Wash, Gentle, Hydrating', false).label")
    drug = page.evaluate("() => likelihood('Anti-Dandruff Shampoo with 1% Ketoconazole, Fresh Scent', false).label")
    assert (kids, drug) == ("Unlikely", "Likely")


def test_category_guess_reads_product_type_and_says_why(page):
    c = page.evaluate("() => catOf('Air Purifier for Home, Captures Pet Allergies, Smoke')")
    assert c["name"] == "Home and garden" and "Purifier" in c["why"]


def test_lmn_item_counts_in_totals_once_reimbursed(page):
    page.evaluate("() => setReimb('TEST-ORDER-2|0', true)")
    page.wait_for_timeout(200)
    assert page.locator(".eq-g").first.inner_text() == "$80.00"  # 60 + the 20 LMN item
    assert page.locator(".eq-r").first.inner_text() == "$20.00"


def test_equation_balances_when_a_40_dollar_lmn_item_is_reimbursed(page):
    page.evaluate("""() => { decisions['TEST-ORDER-2|0'] = Object.assign({}, decisions['TEST-ORDER-2|0'], { amount: 40 }); refreshAll(); setReimb('TEST-ORDER-2|0', true); }""")
    page.wait_for_timeout(200)
    money = lambda e: float(e.inner_text().replace("$", "").replace(",", ""))
    eligible, rollover, reimbursed, not_yet = (money(page.locator(c).nth(n)) for c, n in ((".eq-g", 0), (".eq-g", 1), (".eq-r", 0), (".eq-g", 2)))
    assert (eligible, reimbursed) == (100.0, 40.0)  # 60 + the 40 item, counted in both
    assert eligible + rollover - reimbursed == not_yet == 60.0


def test_electronics_item_with_a_medical_word_is_still_likely(page):
    r = page.evaluate("() => [catOf('Omron Blood Pressure Monitor, Upper Arm Cuff').name, likelihood('Omron Blood Pressure Monitor, Upper Arm Cuff', false).label]")
    assert r == ["Electronics", "Likely"]
    assert page.evaluate("() => likelihood('USB Cable 6ft Braided Charger', false).label") == "Highly unlikely"


def test_save_button_changes_colour_when_there_are_unsaved_changes(page):
    save = page.locator("#saveFile")
    assert "unsaved" not in (save.get_attribute("class") or "")
    page.locator("#list input.ovr-total").first.fill("9.00")
    page.locator("#list input.ovr-total").first.dispatch_event("change")
    page.wait_for_timeout(200)
    assert "unsaved" in save.get_attribute("class")


def test_select_all_can_be_undone(page):
    page.once("dialog", lambda d: d.accept())
    page.evaluate("() => selectAllVisible(true)")
    page.wait_for_timeout(200)
    assert page.locator("#undo").inner_text().startswith("Changed ")
    assert page.locator(".eq-r").first.inner_text() != "$0.00"
    page.locator("#undoLink").click()
    page.wait_for_timeout(200)
    assert page.locator(".eq-r").first.inner_text() == "$0.00"
    assert page.locator("#undo").inner_text() == ""


def test_dates_use_one_format(page):
    import re

    heads = page.locator(".order-head b").all_text_contents()  # includes rows inside closed folds
    assert heads and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", h) for h in heads), heads


def test_what_to_do_first_is_shown_and_can_be_closed_and_remembered(page):
    assert page.locator("#howto").is_visible() and "What to do first" in page.locator("#howto summary").inner_text()
    page.click("#howto summary")
    page.wait_for_function("localStorage.getItem('hsa-howto') === 'closed'", timeout=5000)  # the page records it a moment after the click
    page.reload(wait_until="load")
    page.wait_for_selector("#loading", state="detached", timeout=15000)
    assert page.evaluate("document.getElementById('howto').open") is False  # it stays closed on the next visit


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", "--tb=short", "-p", "no:cacheprovider", __file__]))
