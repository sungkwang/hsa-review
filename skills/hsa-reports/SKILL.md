---
name: hsa-reports
description: Use when building the claim report, the Deductible evidence PDF, or the CSV export. Runs the evidence and page checks first, then builds the report and names any item that still needs a letter or has no image. Reports show statuses; they never decide eligibility.
---

# Reports

The review page builds the reports; this skill is the checks around them.

1. **Check first:** `python tools/check_evidence.py <year>` (no problems) and `python tools/test_review_page.py` (every check PASSED). Stop and report any failure.
2. **Reload** the page (double-click `review.html`, or `python tools/hsa.py open`) so it holds the latest saved decisions, and confirm the status line says Saved (the Save button is not orange). Reports the user keeps go in `<year>/reports/`.
3. **Build** what the user asks for, from the Export menu or the Medical section:
   - **Claim report (PDF):** every item whose status counts as claimable, with paperwork shown as "Not on file" for Doctor's note / LMN items.
   - **Deductible evidence (PDF):** the medical bills with their full-page images. The page waits for the images and refuses to print if one is missing.
   - **Items (CSV):** decisions in the page's own columns.
4. **Name** anything the user should look at: items with Need LMN status, medical entries with no letter, amounts the user edited.
5. **Say** the totals the page shows (Eligible, Reimbursed, Not yet reimbursed) and that they come from the statuses the user set.

Rules: reports show statuses; they never decide eligibility. Do not edit decisions or the data file while building a report.
