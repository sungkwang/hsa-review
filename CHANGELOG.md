# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-16

First version.

### Added
- A "What to do first" box with numbered steps (including when to use Tax %) and a prominent **Change data folder** button.
- The page remembers what you decide about each product by its Amazon product ID (`_app/product_decisions.json`, private, in your data folder) and, on a later purchase of the same product, shows "Suggested: <status> (you decided this on <date>)". It reads every year's file, never applies a suggestion by itself, and forgets what an item taught when you set it back to Undecided.
- The Amazon orders MCP server now lives in `mcp/amazon-orders/` (code only; based on seanoliver/amazon-orders-mcp, MIT License, original `LICENSE` kept), with an MIT `LICENSE` for the whole repository.
- Recovery from a wrong or renamed data folder: the page refuses a year folder, forgets a folder that can no longer be opened and asks again in plain words, and offers **Export ▾ → Change data folder…** and `?reset=1`. Save does nothing when no data was found.
- Double-click `review.html` (Chrome or Edge): the page asks once for your HSA-Review folder, remembers it, lists the years it finds, and reads and saves there directly. `python tools/hsa.py open` and the desktop shortcut remain for other browsers. The rules also load from `skills/hsa-categorize/category_rules.js`, generated from the JSON by `tools/make_rules_js.py` and checked by a test.
- Simple data layout per year: `receipts/` (one level, named `YYYY-MM-DD_type_source_detail`), `reports/`, `decisions.json`, `_app/`. `tools/migrate_layout.py` moves an older folder (plan first, verified backup, then `--confirm`); `decisions.json` keeps the first state of each day in `_app/backups`.
- `hsa.py status` lists documents that are "not identified".
- `skills/hsa-categorize/category_rules.json` (versioned): one rules file for the page and `tools/rules.py`, with a test that both give the same likelihood and category.
- The page loads its data and rules with async fetch, shows "Loading…", and names any missing or broken file.
- `hsa-review` front-door skill, and `python tools/hsa.py shortcut` / the setup step that creates a double-click "HSA Review" shortcut (Windows `.bat`, macOS `.command`) that stays open with a "Next:" message on failure.
- `tools/hsa.py`: `status` (a checklist that names the next step), `setup` (one step at a time, each checked), and `open`; the review page shows the same checklist when a year has no data yet.
- Public eligibility reference at `skills/hsa-categorize/eligibility_reference.md`, in plain words with IRS Publication 502 and 969 links, a review date, and a not-tax-advice notice.
- Data files are `.json` (code is `.js`); `tools/migrate_to_json.py` converts a year once and keeps the old files in the dated backup folder.
- User data now lives in a data folder outside the code folder (`--data-dir`, then `HSA_DATA_DIR`, then `~/.hsa-review/config.json`); tools stop if none is set. `tools/hsa_paths.py` sets and shows it, and `tools/open_review.py` serves the page and the data folder on this computer only.
- The privacy scan fails on any year folder, `images/`, or receipt inside the code folder.
- Persistent Amazon browser profile shared by sign-in and every reader, with one lock, one open per batch, refreshed cookies saved back, and a warning before an order-page batch if the sign-in hour is nearly over.
- Amazon product-page categories and FSA/HSA labels, cached by product ID with the date read; the page uses them first and falls back to a title-word guess that shows which word matched.
- Real order tax, shipping, and discounts split across items by price share (leftover cent to the most expensive item); Tax % is now a fallback.
- Refunded items listed under "Not counted" (folded by default); order totals reflect what was charged.
- Vitamins and supplements, Baby, and "Other (Amazon: path)" categories; drug-ingredient words raise an item to Likely.
- Unsaved-changes colour on Save, a version check that refuses to save over a newer file, and Undo after Select all.
- `tools/organize_files.py` (dry run by default, move log with undo, duplicates by file hash), sample-file rules in the privacy scan, skills `hsa-setup`, `hsa-categorize`, `hsa-reports`, `hsa-organize-files`,
- `tools/check_evidence.py`, `tools/make_samples.py`, `skills/amazon-live-batch`, and a page test runner that prints PASSED or FAILED for each check.

### Changed
- `organize_files.py` now renames inside `<year>/receipts/` (or moves new files in from a folder you choose) with five types (order, bill, receipt, eob, letter); unidentified files keep their names. The Amazon invoice reader names saved invoices `YYYY-MM-DD_order_amazon_<order>.pdf`.
- Scripts and tests moved to `tools/`, starter files and the eligibility reference to `templates/`; private notes moved into a git-ignored folder.
- Personal care is Unlikely; Electronics with a medical word is still Likely.
- Reimbursed Doctor's note / LMN items count in both Eligible and Reimbursed, so the equation balances.
- Dates show as YYYY-MM-DD; lists sort Undecided first, then likelihood, then newest date.
- The "LMN on file" status is removed; use Eligible.
- The sign-in window finishes only when the order history page opens.

### Fixed
- "Vitamins and supplements" (Amazon path) now takes effect for products under Health & Household; the broader Health rule used to win.
- Claim and evidence PDFs were empty; they now print, and wait for large images to load.
- Items on multi-item orders matched the wrong link; parsing now reads both numbers in Amazon's link names.
