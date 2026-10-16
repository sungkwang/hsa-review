---
name: hsa-categorize
description: Use when order items have no Amazon category yet, or new product IDs appear. Asks for approval with the page count and estimated time, reads public product pages (no sign-in), caches category and FSA/HSA signals by product ID with the date read, applies the category table and likelihood rules, and reports what changed.
---

# Categorize products

Rules and sources: `eligibility_reference.md` in this folder (read it when judging an item). For sorting only; not tax advice.

Product pages are live Amazon requests, so the project rules apply: count, estimate, then ask. They need no sign-in, so the one-hour sign-in window does not matter here.

1. **List** the product IDs in the year's data that are not in `<data folder>/<year>/_app/product_cache.json`. The data folder comes from `python tools/hsa_paths.py` (it stops if none is set). Whole-order rows have no product ID until an order-list batch (see `amazon-live-batch`) supplies one.
2. **Tell the user** the count and the estimate (about 5.6 seconds per page) and wait for a yes.
3. **Back up** `<year>/_app/data.json` and the cache to `<data folder>/<year>/_app/backups/<today>/`.
4. **Read** with `python scripts/product_info.py --year <year> ASIN ...` (inside `mcp/amazon-orders`). It reads one page at a time, shows progress and time left, stops on a robot check, and records the category path, the "FSA or HSA eligible" badge, and the date read. It ignores the "FSA Eligible Items" link: that link also appears on non-eligible health pages.
5. **Apply:** rewrite `ASIN_INFO` in the data file from the cache. The page maps Amazon's path to its categories with the rules in `category_rules.json` (the same file the Python tools read) and shows "Category: Amazon (path)" on hover; an unmapped path shows "Other (Amazon: path)" for review.
6. **Check:** `python tools/test_review_page.py` (every check PASSED).
7. **Report:** products read, products with no category (page not found), signals found, and rows whose likelihood changed.

Rules: "no badge" means unknown, not not eligible (3 of 9 items Amazon marked on the order page showed no badge on the product page). Never mark an item eligible from a label; the user decides. Do not read a product that is already cached unless the user asks for a re-check.
