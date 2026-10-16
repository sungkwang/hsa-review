# How it works

**English** | [한국어](HOW_IT_WORKS.ko.md)

This document explains the architecture, component roles, data flow, and MCP mechanics behind HSA Receipt Review.

## Component Roles (Who Does What)

| Component | Role | What it handles |
|---|---|---|
| **You** | Decision-maker | Signs in to Amazon once, approves live tool runs, reviews eligibility in the web dashboard, and approves claim exports. |
| **LLM Agent** | Workflow driver | Interacts via chat (Claude Code, Cursor, Gemini, etc.), calls read-only tools, drafts item eligibility notes against IRS rules, and organizes files. |
| **MCP Server** (`amazon-orders-mcp`) | Data fetcher | Read-only Python service providing MCP tools to fetch Amazon order history, line items, and invoice PDFs safely using your local session. |
| **Review Dashboard** (`review.html`) | Visual interface | Pure HTML/JS browser interface running directly in Chrome/Edge. Reads and writes your local data folder using native browser file access without needing Python. |

## Data Flowchart

```text
 1. Sign In (You)
    └── One-time Amazon login via Chromium window; session cookies stored in ~/.amazon-orders-mcp/

 2. Gather Data (LLM + MCP Server)
    ├── You approve each batch request
    ├── MCP server reads order pages and downloads invoice PDFs into <data folder>/<year>/receipts/
    └── You place medical bills, pharmacy receipts, and EOBs into receipts/

 3. Categorize & Draft (LLM)
    ├── LLM checks items against IRS Publication 502 criteria
    └── Writes processed order data to <data folder>/<year>/_app/data.json

 4. Review & Decide (Review Dashboard — No Python)
    ├── You open review.html directly in Chrome or Edge
    ├── Page connects to your local data folder using native browser File System access
    ├── Set status: Eligible, Not eligible, or Need LMN
    └── Auto-saves choices to <data folder>/<year>/decisions.json

 5. Export (Browser)
    └── Generate Claim Report PDF, Medical Evidence PDF, or CSV export for tax filing
```

## Model Context Protocol (MCP) Mechanics

The Amazon MCP server (`mcp/amazon-orders/`) runs locally as a standard [Model Context Protocol](https://modelcontextprotocol.io) server.

- **Session Handling:** The server uses your authenticated Amazon session saved in `~/.amazon-orders-mcp/cookies.json`. It does not store passwords.
- **Read-Only Operation:** Tools only scrape order lists, order details, and product badges. The server cannot place orders, edit account settings, or add items to cart.
- **Tools Provided:**
  - `refresh_session`: Launches Chromium for sign-in and captures the fresh session.
  - `get_order_history(year)`: Scrapes orders for the requested year.
  - `get_order(order_id)`: Extracts items, prices, sellers, and saves invoice PDFs.
  - `check_asin_eligibility(asin)`: Inspects public Amazon product pages for the "FSA or HSA eligible" badge without requiring sign-in.
- **Safety Boundaries:** Live Amazon order pages require a sign-in active within the last hour (`max_auth_age=3600`). If expired, it halts and requests a session refresh.


## Where data lives

Your data lives in a data folder outside this code folder, so updating or re-downloading the code never touches it. Amazon pages are read with a headless browser and your saved session. Results go to the LLM chat. After you confirm, the agent writes them to the year folder in your data folder. The review page reads that file and saves your decisions beside it.

| File or folder | Contents | Stays local? |
|---|---|---|
| `~/.hsa-review/config.json` | Where your data folder is | Yes. |
| `~/.amazon-orders-mcp/` | Amazon sign-in profile and session cookies (no password) | Yes. Never share it. |
| `<data folder>/<year>/receipts/` | Your documents, one level, named `date_type_source_detail` | Yes. Outside the code folder. |
| `<data folder>/<year>/reports/` | Claim PDF, evidence PDF, CSV exports | Yes. |
| `<data folder>/<year>/decisions.json` | Your decisions and notes | Yes. |
| `<data folder>/<year>/_app/` | Orders (`data.json`), `images/`, `product_cache.json` (Amazon categories with the date read), `product_decisions.json` (what you decided about each product, by product ID), `backups/<date>/`, `logs/`. Not for editing. | Yes. |
| `samples/` (in the code folder) | Fake data in the same layout, for trying the page | No. Public. |
| `.agent/` (in the code folder) | Developer notes and scratch | Git-ignored. |

## The review page

- Double-click `review.html` in Chrome or Edge. The page asks once for your data folder, remembers it, and lists your year folders (it opens the newest, or `?year=2026`). The browser may ask you to allow access again on a later visit.
- In a browser without folder access (Firefox, Safari), run `python tools/hsa.py open`. This starts a small server on your computer only; it shows the page and your data folder and nothing else.
- Saves decisions to the year folder after you pick it once. Firefox and other browsers without folder access show a message; use Export (CSV) there.
- Each eligible item has **Mark reimbursed**. The totals split eligible amounts into reimbursed and not yet reimbursed.
- `YEAR_CONFIG` in the year's data file sets a rollover (`priorUnreimbursed`) and a threshold. Both default to 0.
- **Not yet reimbursed** is an accounting figure, not a withdrawal amount. What you can withdraw depends on your HSA balance and plan rules.

## Logs

There is no log file. Messages appear where each tool runs.

- **MCP server:** `Starting ... Server`, `Amazon session expired; opening the sign-in window`, `timed out`, `could not read the page`, and tracebacks for unexpected errors.
- **Scripts:** progress lines, then a summary of `saved`, `skipped` (never overwritten), and `error` per order.
- **Review page:** a status line such as `Saved to 2026/hsa_decisions_2026.json at 10:42:05`.
- **Privacy:** messages can include order numbers, item names, or page text. Don't paste them into public issues.

## Limits

- An Amazon layout change breaks the parsers until they are updated. The error names the page.
- The "FSA or HSA eligible" label is Amazon's merchant marking, not an IRS ruling. Check the product page before relying on it.
- Only Amazon.com (US) is supported.
- The transactions page shows about ten days only, so it isn't used.

## Before printing the medical evidence PDF

Run `python tools/check_evidence.py 2026`. It fails if a medical entry has no image, a PDF has more pages than images, or a file in the year folder belongs to no entry. The PDF button also stops with a message when an image cannot load, instead of printing a blank page.
