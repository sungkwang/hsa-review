# HSA receipt review: setup and rules for an LLM agent

This project helps one household review HSA-eligible purchases for one tax year. Personal receipts, order data, cookies, and decisions stay on the local computer, in a data folder outside this code folder. Never commit them. Read `HOW_IT_WORKS.md` for the jobs, the data flow, and the logs.

## First use

The front door is the `hsa-review` skill ("open my HSA review"). On first use, run `python tools/hsa.py status` and guide the user through the next unchecked step, one at a time. The checklist comes from the program, not from you, so every agent follows the same steps. `python tools/hsa.py setup` walks the early steps and checks each one. Every failure ends with "Next:" and one action; say that action to the user in plain words.

## One-time setup (the details behind those steps)

1. Install Python 3.11 or 3.12.
2. Install the Amazon MCP server that is part of this repository: from this folder run `pip install -e mcp/amazon-orders` and `python -m playwright install chromium`.
3. Register the server: copy `.mcp.json.example` to `.mcp.json`. The `amazon-orders-mcp` command must run from the environment where you installed it. Restart the LLM agent, then confirm `amazon-orders` is connected.
4. Choose a data folder outside this code folder. Suggested: `python tools/hsa_paths.py --suggest` (Documents/HSA-Review on Windows, ~/HSA-Review elsewhere). Save it with `python tools/hsa_paths.py --set <folder>`. In it create a year folder, for example `2026/`, and `images/`. Copy the templates:
   - `templates/hsa_data_example.json` to `<data folder>/2026/_app/data.json`
   - `templates/hsa_decisions_example.json` to `<data folder>/2026/decisions.json`
   - also create `2026/receipts/` and `2026/reports/`. (`python tools/hsa.py setup` does all of this.)
5. Sign in once: call the `refresh_session` tool and sign in to Amazon in the browser window that opens. Alternatively, run `python cookie_capture.py` inside `mcp/amazon-orders`.
6. Tell the user to double-click `review.html` in Chrome or Edge and choose the data folder when asked (once; the page remembers it). Other browsers: run `python tools/hsa.py open`. To try the page on fake data first, choose the `samples` folder.

## Rules for the agent

- Read-only Amazon tools: `get_order_history(year)`, `get_order(order_id)`, and `check_asin_eligibility(asin)`. Check eligibility only for candidate items, not every order.
- Every live Amazon request needs the user's approval first. Offline tests and template files never contact Amazon.
- Amazon order pages need a sign-in from the last hour (`max_auth_age=3600`); product pages do not. Sign in, then run order pages first, one request at a time, and stop on any sign-in or verification page (say "sign in needed", resume from that order).
- Judge eligibility with `skills/hsa-categorize/eligibility_reference.md`, and say which rule applied. An "FSA or HSA eligible" label from Amazon is a candidate signal, not a plan decision.
- Write decisions only after the user confirms them.
- Do not paste order details, names, or addresses into issues, commits, or shared notes.

## Repository rules

- Never commit year folders, `images/`, PDFs, CSVs, `cookies.json`, or `.mcp.json`. User data lives outside this folder, and `python tools/check_personal_data.py` fails if a year folder or receipt is found inside it. `.gitignore` is a second layer.
- Run the offline tests of the MCP server with `pytest` inside `mcp/amazon-orders`. They use synthetic data and make no Amazon requests.
- Before sharing or committing, run `python tools/check_personal_data.py`. It must report clean.

## Folders

- Public files live in the top-level docs and in `skills/`, `tools/`, `templates/`, and `samples/`.
- `.agent/` is private and git-ignored. `.agent/scratch/` is disposable. `.agent/docs/` holds the owner's notes and must never be deleted or cleaned. A cleanup step may touch only `.agent/scratch/`.
- Two locations. The code folder (this repository) holds the program, `samples/`, and no user data. The data folder holds one folder per year (`receipts/`, `reports/`, `decisions.json`, `_app/`); it is found by `--data-dir`, then `HSA_DATA_DIR`, then `~/.hsa-review/config.json`, and a tool stops with "No data folder set. Run setup." if none is set. Never fall back to the code folder.
- `samples/2025/` has the same layout as a real year folder; use it with `--data-dir samples`.
- Nothing in `.agent/` or the data folder may be referenced in public files.
