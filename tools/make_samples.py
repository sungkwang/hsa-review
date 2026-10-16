"""Generates the fake sample data set in samples/. Every value here is invented.

Real files are never read or copied. Order numbers start with 900-, product IDs are BFAKE#####,
people and places are fictional, and every PDF has its metadata removed.
Run:  python tools/make_samples.py
"""

import io
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

OUT = Path(__file__).resolve().parent.parent / "samples" / "2025"

ENT_BILL = """<html><body style="font-family:Arial,sans-serif;font-size:13px;margin:36px">
<h2>Sample ENT Clinic</h2><div>123 Example St, Exampleville, EX 00000 · (000) 555-0100</div><hr>
<table style="width:100%"><tr><td><b>Patient:</b> Alex Example</td><td><b>Member ID:</b> EX000000</td></tr>
<tr><td><b>Statement date:</b> 2025-06-09</td><td><b>Plan:</b> Example Health Plan</td></tr></table>
<table style="width:100%;border-collapse:collapse;margin-top:16px">
<tr style="background:#eee"><th align=left>Date of service</th><th align=left>Description</th><th align=right>Charge</th><th align=right>Plan paid</th><th align=right>You owe</th></tr>
<tr><td>2025-06-09</td><td>Office visit, established patient</td><td align=right>$220.00</td><td align=right>$107.01</td><td align=right>$112.99</td></tr></table>
<p style="margin-top:24px"><b>Amount due: $112.99</b></p><p>Payment received 2025-06-09, card ending 0000. Thank you.</p>
<p style="color:#666">SAMPLE DATA: this document is fictional.</p></body></html>"""


def html_to_pdf(html: str, path: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        data = page.pdf(format="Letter")
        browser.close()
    reader = PdfReader(io.BytesIO(data))
    writer = PdfWriter()
    for pg in reader.pages:
        writer.add_page(pg)
    writer.add_metadata({"/Title": "", "/Author": "", "/Creator": "", "/Producer": "", "/Subject": "", "/Keywords": ""})
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        writer.write(f)


if __name__ == "__main__":
    html_to_pdf(ENT_BILL, OUT / "receipts" / "2025-06-09_bill_Sample-ENT-Clinic_visit.pdf")
    print("wrote", OUT / "receipts" / "2025-06-09_bill_Sample-ENT-Clinic_visit.pdf")
