---
name: amazon-live-batch
description: Run an approved batch of live Amazon requests for the HSA receipt project (order summary pages, order lists, product pages) safely. Use whenever a task needs to contact Amazon, such as re-fetching orders, reading product categories or FSA/HSA labels, saving invoices, or checking eligibility.
---

# Live Amazon batch

For any LLM agent. This is plain Markdown and plain shell commands; nothing here needs one vendor's tools. Where a step says "sign in", use whichever of these your agent has: the `refresh_session` tool of the `amazon-orders` MCP server, or, in a terminal, `python cookie_capture.py` from `mcp/amazon-orders`. If your agent has no skill system, read this file at the start of any task that contacts Amazon.

Amazon requests need the user's yes for each batch. Order pages also need a sign-in from the last hour (Amazon's `max_auth_age=3600`); product pages need no sign-in.

## Steps

1. **Plan the batch.** Count the page loads, split them into order pages and product pages, and give the estimate: order pages about 3.6 s each, product pages about 5.6 s each.
2. **Check the sign-in hour.** Print the minutes left with `python -c "from amazon_orders_mcp.browser_profile import sign_in_minutes_left as m; print(m())"` (run in the Python environment where the server is installed). `None` means no sign-in is on record. The same time is in `~/.amazon-orders-mcp/last_sign_in.txt` (a Unix time, seconds). If more than 50 minutes have passed, or the order-page estimate is longer than the minutes left, or the file is missing, sign in first: start the sign-in (tool or command above) and tell the user to sign in in the window. The user types the password and any 2-step code; an agent never fills them. The sign-in window opens the order history and finishes only when that page loads: an old cookie is not enough, because Amazon asks for a fresh sign-in on order pages even when the account page opens. After changing the MCP server code, reconnect the server first.
3. **Ask for approval** with the counts and estimates. Do not start before the user says yes. A user's earlier yes for a different batch does not count.
4. **Back up** the data file to `<data folder>/<year>/_app/backups/<today>/` before any write. The data folder comes from `python tools/hsa_paths.py` (it stops if none is set).
5. **Order pages first**, then product pages, one request at a time with about 0.5 s between requests. Use `fetch_print_pages` in `print_fetch.py` in the `amazon_orders_mcp` package (`mcp/amazon-orders/src`) for order pages (one browser per batch, one lock) and `python scripts/product_info.py --year <year> ASIN...` (inside `mcp/amazon-orders`) for product pages. Show progress as `done/total`, time elapsed, and time left.
6. **Stop** on a sign-in, verification, or robot-check page. Say "sign in needed", do not count that item as failed, list what is done, and resume from that item after sign-in. Log only the sign-in address summary (path, parameter names, `max_auth_age`), never cookies or personal data.
7. **Verify** after writing: run `python tools/test_review_page.py` in the project root (it must print PASSED for every check) and `python tools/check_evidence.py <year>`.
8. **Report** counts: done, missing, and anything that needs the user's decision. Keep order details out of issues, commits, and shared notes.

## Rules

- Run Python from the environment named in the project's agent rules, with script files, not long inline code.

- No random timing; keep a steady pace.
- Treat "no label" as unknown, not as not eligible.
- Cache by product ID with the date read; do not re-read a cached product.
- Never write year folders, images, cookies, or the browser profile into git.
