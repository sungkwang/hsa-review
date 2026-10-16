"""Tests for opening the page by double-click: it asks for the HSA-Review folder, remembers it, and reads and
saves there directly. The browser's picker cannot be driven in a test, so the "picked" folder is a folder in the
browser's private storage; everything after the click is the page's real folder-mode code.

The page is served by a plain static server (no launcher), which makes it fall into folder mode.

Run:  python tools/test_folder_mode.py
"""

import copy
import json
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import testserver  # noqa: E402
from test_review_page import DATA, DECISIONS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
pw = pytest.importorskip("playwright.sync_api")

PNG = [137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0, 1, 0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0, 0, 13, 73, 68, 65, 84, 120, 156, 99, 248, 255, 255, 63, 0, 5, 254, 2, 254, 167, 53, 129, 132, 0, 0, 0, 0, 73, 69, 78, 68, 174, 66, 96, 130]

BUILD_FOLDER = """async ([data, decisions, layout, png]) => {
  const root = await navigator.storage.getDirectory();
  for await (const [name] of root.entries()) await root.removeEntry(name, { recursive: true });
  const hsa = await root.getDirectoryHandle("HSA-Review", { create: true });
  const y = await hsa.getDirectoryHandle("2099", { create: true });
  const put = async (dir, name, content) => { const w = await (await dir.getFileHandle(name, { create: true })).createWritable(); await w.write(content); await w.close(); };
  if (layout === "new") {
    const app = await y.getDirectoryHandle("_app", { create: true });
    await put(app, "data.json", JSON.stringify(data));
    await put(y, "decisions.json", JSON.stringify(decisions));
    await put(await app.getDirectoryHandle("images", { create: true }), "abc.jpg", new Uint8Array(png));
  } else {
    await put(y, "hsa_data_2099.json", JSON.stringify(data));
    await put(y, "hsa_decisions_2099.json", JSON.stringify(decisions));
    await put(await hsa.getDirectoryHandle("images", { create: true }), "abc.jpg", new Uint8Array(png));
  }
  window.__hsaRoot = hsa;
  window.showDirectoryPicker = async () => hsa;
  return true;
}"""

READ_FILE = """async (parts) => {
  let dir = await (await navigator.storage.getDirectory()).getDirectoryHandle("HSA-Review");
  try {
    for (const p of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(p);
    return await (await (await dir.getFileHandle(parts[parts.length - 1])).getFile()).text();
  } catch (e) { return null; }
}"""

WRITE_FILE = """async ([parts, text]) => {
  let dir = await (await navigator.storage.getDirectory()).getDirectoryHandle("HSA-Review");
  for (const p of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(p);
  const w = await (await dir.getFileHandle(parts[parts.length - 1], { create: true })).createWritable();
  await w.write(text);
  await w.close();
}"""


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture()
def site():
    server, port = testserver.start(lambda p: [sys.executable, "-m", "http.server", str(p), "--bind", "127.0.0.1", "--directory", str(ROOT)])
    url = f"http://127.0.0.1:{port}/review.html?year=2099"
    try:
        with pw.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            yield browser, url
            browser.close()
    finally:
        server.terminate()


def open_page(browser, url, layout="new", data=None):
    page = browser.new_page(viewport={"width": 1100, "height": 900})
    page.errors = []
    page.on("pageerror", lambda e: page.errors.append(str(e)))
    try:
        page.goto(url, wait_until="load", timeout=15000)
    except pw.TimeoutError:  # the code folder is in Dropbox, which can briefly hold review.html while it syncs
        page.goto(url, wait_until="load", timeout=30000)
    page.wait_for_selector("#opener", state="visible", timeout=10000)
    page.evaluate(BUILD_FOLDER, [data or DATA, DECISIONS, layout, PNG])
    return page


def choose_folder(page):
    page.click("#changeFolder")
    page.wait_for_selector("#loading", state="detached", timeout=15000)


def test_the_page_asks_for_the_folder_then_reads_it_and_shows_images(site):
    browser, url = site
    data = copy.deepcopy(DATA)
    data["ORDERS"][0]["items"][0]["img"] = "abc"
    page = open_page(browser, url, data=data)
    assert "Choose receipts folder" in page.locator("#openerText").inner_text()
    choose_folder(page)
    assert page.errors == []
    assert page.locator("#list .order").count() == 1 and page.locator("#lmn .order").count() == 1
    assert page.evaluate("[...document.querySelectorAll('#yearPick option')].map(o => o.value)") == ["2099"]
    assert page.evaluate("(() => { const i = document.querySelector('#list img.thumb'); return i.src.startsWith('blob:') && i.complete && i.naturalWidth === 1; })()")


def test_the_remembered_folder_is_used_on_the_next_visit_without_asking(site):
    browser, url = site
    page = open_page(browser, url)
    choose_folder(page)
    page.reload(wait_until="load")
    page.wait_for_selector("#loading", state="detached", timeout=15000)  # no click needed: access was already granted
    assert page.locator("#opener").is_hidden() and page.locator("#list .order").count() == 1


def test_save_writes_decisions_next_to_the_data_and_keeps_the_days_first_state(site):
    browser, url = site
    page = open_page(browser, url)
    choose_folder(page)
    page.locator("#list input.ovr-total").first.fill("9.00")
    page.locator("#list input.ovr-total").first.dispatch_event("change")
    page.click("#saveFile")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Saved to 2099/decisions.json')", timeout=10000)
    saved = json.loads(page.evaluate(READ_FILE, ["2099", "decisions.json"]))
    assert saved["__version"] == 1 and saved["TEST-ORDER-1|0"]["amount"] == 9
    backup = json.loads(page.evaluate(READ_FILE, ["2099", "_app", "backups", date.today().isoformat(), "decisions.json"]))
    assert backup == DECISIONS  # the state before today's first save


def test_a_save_over_a_newer_file_is_refused(site):
    """What the two-tab test checks by hand: another tab saved after this page loaded."""
    browser, url = site
    page = open_page(browser, url)
    choose_folder(page)
    newer = json.dumps({**DECISIONS, "__version": 5})
    page.evaluate(WRITE_FILE, [["2099", "decisions.json"], newer])
    page.locator("#list input.ovr-total").first.fill("9.00")
    page.locator("#list input.ovr-total").first.dispatch_event("change")
    page.click("#saveFile")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Not saved')", timeout=10000)
    assert "Reload the page" in page.locator("#status").inner_text()
    assert page.evaluate(READ_FILE, ["2099", "decisions.json"]) == newer


def test_the_older_flat_layout_still_opens_and_saves_to_its_own_file_name(site):
    browser, url = site
    page = open_page(browser, url, layout="old")
    choose_folder(page)
    assert page.errors == [] and page.locator("#list .order").count() == 1
    page.locator("#list input.ovr-total").first.fill("9.00")
    page.locator("#list input.ovr-total").first.dispatch_event("change")
    page.click("#saveFile")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Saved to 2099/hsa_decisions_2099.json')", timeout=10000)


REPEAT = copy.deepcopy(DATA)  # the same product (BFAKE00010) bought in two orders
REPEAT["ORDERS"][2]["items"][0]["asin"] = "BFAKE00010"
REPEAT["ORDERS"].append({"date": "January 8, 2099", "id": "TEST-ORDER-4", "total": 5, "items": [{"t": "Plain Cable", "p": 5, "seller": "Seller C", "marked": False, "img": "", "asin": "BFAKE00010"}]})

PUT_PRIOR_YEAR = """async ([year, name, text]) => {
  const hsa = await (await navigator.storage.getDirectory()).getDirectoryHandle("HSA-Review");
  const app = await (await hsa.getDirectoryHandle(year, { create: true })).getDirectoryHandle("_app", { create: true });
  const w = await (await app.getFileHandle(name, { create: true })).createWritable();
  await w.write(text);
  await w.close();
}"""


def set_status(page, key, status):
    page.evaluate("document.querySelectorAll('details.fold').forEach(d => d.open = true)")  # the plain cable is in a folded list
    page.select_option(f'select[data-k="{key}"]', status)
    page.wait_for_timeout(200)


def test_a_status_you_set_is_remembered_by_product_and_suggested_on_the_next_purchase(site):
    browser, url = site
    page = open_page(browser, url, data=REPEAT)
    choose_folder(page)
    page.evaluate("document.querySelectorAll('details.fold').forEach(d => d.open = true)")
    assert page.locator('.suggest').count() == 0  # nothing remembered yet
    set_status(page, "TEST-ORDER-3|0", "Not eligible")
    page.click("#saveFile")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Saved to')", timeout=10000)
    saved = json.loads(page.evaluate(READ_FILE, ["2099", "_app", "product_decisions.json"]))
    assert saved == {"BFAKE00010": {"status": "Not eligible", "date": date.today().isoformat(), "by": "TEST-ORDER-3|0"}}
    page.evaluate("document.querySelectorAll('details.fold').forEach(d => d.open = true)")
    later = page.locator('section.order:has(select[data-k="TEST-ORDER-4|0"])')
    assert f"Suggested: Not eligible (you decided this on {date.today().isoformat()})" in later.inner_text()
    assert later.locator("select").input_value() == "Undecided"  # a suggestion only: never applied by itself


def test_suggestions_also_come_from_earlier_years(site):
    browser, url = site
    page = open_page(browser, url, data=REPEAT)
    page.evaluate(PUT_PRIOR_YEAR, ["2098", "product_decisions.json", json.dumps({"BFAKE00010": {"status": "Need LMN", "date": "2098-05-26", "by": "OLD-ORDER|0"}})])
    choose_folder(page)
    page.evaluate("document.querySelectorAll('details.fold').forEach(d => d.open = true)")
    text = page.locator("#all").inner_text()
    assert text.count("Suggested: Doctor's note / LMN (you decided this on 2098-05-26)") == 2  # both purchases of that product


def test_setting_a_status_back_to_undecided_forgets_what_that_item_taught(site):
    browser, url = site
    page = open_page(browser, url, data=REPEAT)
    choose_folder(page)
    set_status(page, "TEST-ORDER-3|0", "Eligible")
    page.evaluate("document.querySelectorAll('details.fold').forEach(d => d.open = true)")
    assert "Suggested" in page.locator('section.order:has(select[data-k="TEST-ORDER-4|0"])').inner_text()
    assert "Suggested" not in page.locator('section.order:has(select[data-k="TEST-ORDER-3|0"])').inner_text()  # an item never suggests to itself
    set_status(page, "TEST-ORDER-3|0", "Undecided")
    page.evaluate("document.querySelectorAll('details.fold').forEach(d => d.open = true)")
    assert "Suggested" not in page.locator('section.order:has(select[data-k="TEST-ORDER-4|0"])').inner_text()


def test_the_older_flat_layout_keeps_its_product_decisions_in_its_own_file(site):
    browser, url = site
    page = open_page(browser, url, layout="old", data=REPEAT)
    choose_folder(page)
    set_status(page, "TEST-ORDER-3|0", "Eligible")
    page.click("#saveFile")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Saved to')", timeout=10000)
    assert json.loads(page.evaluate(READ_FILE, ["2099", "product_decisions_2099.json"]))["BFAKE00010"]["status"] == "Eligible"


def test_the_folder_box_sits_below_the_header(site):
    browser, url = site
    page = open_page(browser, url)  # the folder box is showing, waiting for a click
    title, box = (page.locator(s).first.bounding_box() for s in ("h1", "#opener"))
    assert box["y"] > title["y"] + title["height"]  # below the title row, not above the header


def test_the_instructions_are_four_numbered_steps_in_one_row_that_explain_tax_percent(site):
    browser, url = site
    page = open_page(browser, url)
    steps = page.locator("#howto ol.steps li")
    assert steps.count() == 4
    texts = steps.all_inner_texts()
    assert texts[0].startswith("Set Tax %") and "price without tax" in texts[0] and "don't use it" in texts[0]
    assert texts[1].startswith("Choose a status") and texts[2].startswith("Tick Reimbursed") and texts[3].startswith("Save")
    assert page.locator("#howto .sp").count() == 0  # plain words, no pills
    assert "counter(step)" == page.evaluate("getComputedStyle(document.querySelector('#howto ol.steps li'), '::before').content")
    tops = [round(li.bounding_box()["y"]) for li in steps.all()]
    assert len(set(tops)) == 1  # one row at the normal page width
    assert "Choose receipts folder" in page.locator("#howto .why-folder").inner_text()  # the folder note is on top


def test_a_finished_step_shows_a_check_mark(site):
    browser, url = site
    page = open_page(browser, url)
    choose_folder(page)
    assert page.locator("#step-tax.done").count() == 0  # Tax % is empty
    assert page.locator("#step-save.done").count() == 1  # decisions exist and nothing is unsaved
    page.fill("#taxRate", "7")
    assert page.locator("#step-tax.done").count() == 1  # Tax % filled in
    page.locator("#list input.ovr-total").first.fill("9.00")
    page.locator("#list input.ovr-total").first.dispatch_event("change")
    assert page.locator("#step-save.done").count() == 0  # a change is waiting to be saved
    page.click("#howtoSave")  # the Save button inside the card
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Saved to')", timeout=10000)
    assert page.locator("#step-save.done").count() == 1  # nothing left unsaved


def test_one_outlined_folder_button_shows_the_folder_name_once_a_folder_is_open(site):
    browser, url = site
    page = open_page(browser, url)
    assert page.locator("#changeFolder").inner_text().strip() == "Choose receipts folder"  # no folder yet: the button says what it does
    choose_folder(page)
    assert page.locator("#changeFolder").inner_text().strip() == "📁 HSA-Review"  # folder open: the same button shows its name
    style = page.evaluate("(() => { const s = getComputedStyle(document.getElementById('changeFolder')); return [s.borderTopWidth, parseInt(s.fontWeight), s.fontSize]; })()")
    assert style == ["2px", 700, "15px"]


def test_header_layout_year_beside_title_then_folder_tax_export_save(site):
    browser, url = site
    page = open_page(browser, url)
    choose_folder(page)
    box = lambda sel: page.locator(sel).first.bounding_box()  # noqa: E731
    parts = [box(sel) for sel in ("h1", "#yearPick", "#changeFolder", ".tax-box", ".menu > summary", "#saveFile", "#langToggle")]
    xs = [b["x"] for b in parts]
    assert xs == sorted(xs)  # title, year, folder button, Tax, Export, Save, language switch
    centres = [b["y"] + b["height"] / 2 for b in parts]
    assert max(centres) - min(centres) < 3  # one line, centred together


def test_choosing_a_year_folder_by_mistake_is_refused_and_forgotten(site):
    """Seen in real use: the page used to ask for the year folder, so people pick it. Nothing may be written."""
    browser, url = site
    page = open_page(browser, url)
    page.evaluate("window.showDirectoryPicker = async () => window.__hsaRoot.getDirectoryHandle('2099')")  # the year folder itself
    page.click("#changeFolder")
    page.wait_for_function("document.getElementById('openerText').textContent.includes('single year folder')", timeout=10000)
    assert page.locator("#opener").is_visible()
    assert page.evaluate(READ_FILE, ["2099", "2099", "decisions.json"]) is None  # nothing was created inside the year folder
    page.reload(wait_until="load")  # the wrong folder was forgotten, so the page asks again instead of reopening it
    page.wait_for_selector("#opener", state="visible", timeout=10000)
    assert "Choose receipts folder" in page.locator("#openerText").inner_text()


def test_a_remembered_folder_that_was_renamed_is_forgotten_and_the_page_asks_again(site):
    """Seen in real use: the folder was renamed, and the page showed a raw browser error."""
    browser, url = site
    page = open_page(browser, url)
    choose_folder(page)
    page.evaluate("async () => { const root = await navigator.storage.getDirectory(); await root.removeEntry('HSA-Review', { recursive: true }); }")
    page.reload(wait_until="load")
    page.wait_for_selector("#opener", state="visible", timeout=10000)
    assert "could not be opened" in page.locator("#openerText").inner_text()
    assert page.locator(".load-error").count() == 0  # a plain message and a button, not a raw browser error
    page.evaluate(BUILD_FOLDER, [DATA, DECISIONS, "new", PNG])  # the folder is back (renamed again): choosing it works
    page.click("#changeFolder")
    page.wait_for_selector("#loading", state="detached", timeout=15000)
    assert page.locator("#list .order").count() == 1


def test_reset_in_the_address_forgets_the_remembered_folder(site):
    browser, url = site
    page = open_page(browser, url)
    choose_folder(page)
    page.goto(url + "&reset=1", wait_until="load")
    page.wait_for_selector("#opener", state="visible", timeout=10000)
    assert "Choose receipts folder" in page.locator("#openerText").inner_text()


def test_before_a_folder_is_chosen_only_the_welcome_the_folder_button_and_the_instructions_show(site):
    browser, url = site
    page = open_page(browser, url)
    assert "Welcome to HSA receipt review" in page.locator("#opener h2").inner_text()
    for sel in ("#yearPick", ".tax-box", ".menu", "#saveFile", ".status-row"):
        assert not page.locator(sel).first.is_visible(), sel
    assert page.locator("#changeFolder").is_visible() and page.locator("#howto").is_visible()
    for sel in ("#selectbar", ".toolbar", "#lmn", "#medical", "#list", "#all", "#skipped-wrap", "#unconf-h"):
        assert not page.locator(sel).first.is_visible(), sel  # no empty sections under the welcome box
    choose_folder(page)
    for sel in ("#yearPick", ".tax-box", ".menu", "#saveFile"):
        assert page.locator(sel).first.is_visible(), sel


def test_each_order_links_its_invoice_and_amazon_page_and_each_item_its_product_page(site):
    browser, url = site
    page = open_page(browser, url)
    page.evaluate("async () => { const r = await (await window.__hsaRoot.getDirectoryHandle('2099')).getDirectoryHandle('receipts', { create: true }); const w = await (await r.getFileHandle('2099-01-05_order_amazon_TEST-ORDER-1.pdf', { create: true })).createWritable(); await w.write('%PDF-1.4'); await w.close(); }")
    choose_folder(page)
    first = page.locator("#list .order").first
    assert first.locator("a.inv").inner_text() == "Invoice PDF"  # the saved file exists
    assert page.evaluate("getComputedStyle(document.querySelector('a.inv'), '::before').content") == '"📄 "'  # a PDF icon, not the cart icon
    assert first.locator("a[href*='order-details?orderID=TEST-ORDER-1']").inner_text() == "Order page"
    other = page.locator("#all .order .noinv").first  # no invoice saved for this one
    assert other.inner_text() == "No invoice" and other.get_attribute("title") == "Download with the next Amazon pull."
    assert page.evaluate("orderLink('900-1234567-1234567', '2099-01-01')").count("order-details") == 0  # fake sample order: no Amazon link
    assert page.evaluate("productLink('BFAKE00001')") == ""
    assert "dp/B012345678" in page.evaluate("productLink('B012345678')")


def test_change_folder_resets_the_page_only_when_a_different_folder_is_chosen(site):
    browser, url = site
    page = open_page(browser, url)
    choose_folder(page)
    page.evaluate("window.__stay = true")
    page.click("#changeFolder")  # the picker offers the same folder again: nothing changes
    page.wait_for_timeout(500)
    assert page.evaluate("window.__stay") is True
    page.evaluate("async () => { const other = await window.__hsaRoot.getDirectoryHandle('other', { create: true }); window.showDirectoryPicker = async () => other; }")
    page.click("#changeFolder")  # a different folder: the page reloads
    page.wait_for_function("window.__stay !== true", timeout=10000)


def test_save_never_creates_folders_when_no_data_was_found(site):
    browser, url = site
    page = open_page(browser, url)
    page.evaluate("async () => { const empty = await window.__hsaRoot.getDirectoryHandle('empty', { create: true }); window.showDirectoryPicker = async () => empty; }")
    choose_folder(page)
    page.click("#saveFile")
    page.wait_for_function("document.getElementById('status').textContent.startsWith('Nothing to save')", timeout=10000)
    assert page.evaluate("async () => { const d = await window.__hsaRoot.getDirectoryHandle('empty'); const n = []; for await (const [name] of d.entries()) n.push(name); return n; }") == []


def test_a_browser_without_folder_access_says_so_and_names_the_other_way(site):
    browser, url = site
    page = browser.new_page()
    page.add_init_script("delete window.showDirectoryPicker")
    page.goto(url, wait_until="load")
    page.wait_for_selector(".load-error", timeout=10000)
    text = page.locator(".load-error").inner_text()
    assert "cannot open folders" in text and "python tools/hsa.py open" in text


def test_when_opened_from_disk_the_page_offers_the_folder_picker():
    with pw.sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto((ROOT / "review.html").as_uri() + "?year=2099", wait_until="load")
        page.wait_for_selector("#opener", state="visible", timeout=10000)
        assert "Choose receipts folder" in page.locator("#openerText").inner_text() and errors == []
        browser.close()


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "--tb=short", "-p", "no:cacheprovider", __file__]))
