# HSA receipt review

Review one tax year of HSA-eligible purchases. It pulls your Amazon order history, checks items against the "FSA or HSA eligible" label, and gives you a local page to record decisions and export them.

**Not tax advice.** Check your HSA administrator's rules before you claim anything.

## Files

- `review.html`: the review page. Double-click it (Chrome or Edge).
- `AGENTS.md` (and `CLAUDE.md`, which points to it): setup steps and rules for an LLM agent.
- `HOW_IT_WORKS.md`: where data lives, the review page, logs, and limits.
- `templates/`: starter files for a year folder (`hsa_data_example.json`, `hsa_decisions_example.json`). The eligibility rules summary is `skills/hsa-categorize/eligibility_reference.md`.
- `tools/`: `check_personal_data.py` (privacy scan, with tests), `check_evidence.py` (every medical bill has an image), `test_review_page.py` (checks the review page; run `python tools/test_review_page.py`), `organize_files.py` (sorts new PDFs into the year folder; plan only unless you add `--confirm`), `make_samples.py` (fake sample data, work in progress).
- `skills/`: short task guides for LLM agents (see Skills below), and `skills/hsa-categorize/category_rules.json`, the one rules file read by the page and the Python tools.
- `samples/`: fake data for trying the page and for tests.
- `mcp/amazon-orders/`: the Amazon orders MCP server (code only), based on seanoliver/amazon-orders-mcp (MIT License).
- `.mcp.json.example`: registration for the Amazon MCP server.

## Ways to start

- **Double-click `review.html`** (Chrome or Edge). The first time, the page asks you to choose your HSA-Review data folder. It remembers the folder, so later visits need one click on "Allow". It reads and saves your data there directly: no server, no Python.
- **Picked the wrong folder, or renamed it?** The page says so and asks again. You can also use **Export ▾ → Change data folder…**, or add `?reset=1` to the page address, to make it forget the remembered folder. (The page remembers it inside the browser; there is no file to delete.) Choose the folder that *contains* your year folders (`HSA-Review`), not a year folder.
- **Firefox or Safari** cannot open folders from a page. Use the **HSA Review** shortcut that `python tools/hsa.py setup` offers to put on your desktop (`python tools/hsa.py shortcut` makes it later), or run `python tools/hsa.py open`. If something fails, the window stays open and says what to do next.
- **With an agent:** say "open my HSA review" (Claude Code: `/hsa-review`). It checks where you are and guides the next step.
- **Not sure where you are?** `python tools/hsa.py status` lists each step as done or not and names the next one.

## Two locations: code and your data

- **This folder is the program.** You can replace it, re-download it, or `git pull` it. It holds no personal data.
- **Your data folder is yours.** Year folders, receipts, images, reports, backups, and the product cache live there, by default `Documents/HSA-Review/` (Windows) or `~/HSA-Review/` (macOS, Linux). Tools find it from `--data-dir`, then the `HSA_DATA_DIR` variable, then `~/.hsa-review/config.json` (written by `python tools/hsa_paths.py --set <folder>`). If none is set they stop and say so; they never use the code folder.
- `samples/2025/` has the same layout as a real year folder, so you can try everything by choosing the `samples` folder (or `--data-dir samples`).

Inside your data folder, each year has just these:

```
HSA-Review/
  2026/
    receipts/        all your documents, one level, named YYYY-MM-DD_type_source_detail.ext
    reports/         claim PDF, evidence PDF, CSV exports
    decisions.json   your choices (the first state of each day is backed up automatically)
    _app/            the app's own files: orders, images, product cache, backups, logs (not for editing)
```

The type in a document name is one of `order`, `bill`, `receipt`, `eob`, `letter`, for example `2026-08-12_bill_ENT-clinic_visit.pdf`. Sorting by name sorts by date, and typing `_bill_` in the File Explorer search box shows only bills. `python tools/organize_files.py` names new documents for you: it prints a plan first, renames only after you add `--confirm`, keeps an undo log, and skips duplicates. A file it cannot identify keeps its name, and `python tools/hsa.py status` lists it as "not identified". An older flat layout still opens; `python tools/migrate_layout.py` moves it (plan first, verified backup, then `--confirm`).

## Who does what

| Step | You | LLM agent | Python (MCP server, scripts, review page) |
|---|---|---|---|
| Setup | Sign in once, including 2FA | Reads `AGENTS.md`, installs, registers the server | Installs the server; saves the session cookies |
| Pull orders | Approve each live Amazon request | Calls read-only tools; drafts items and eligibility notes | Reads order pages with a headless browser; fails loudly if a page changed |
| Check candidates | Approve the batch | Checks candidate items only | Reads public product pages; no sign-in |
| Decide | Set status, notes, and reimbursed on the page; export CSV | Never decides for you; asks before writing data files | Auto-saves decisions; computes totals and the claim report |

```
 Sign in once (you)
        │
        ▼
 Approve a pull (you) ──► LLM calls read-only tools ──► Python reads order pages
                                                                 │
                                                                 ▼
 LLM drafts items and notes ◄──────────────────────────── order data (JSON)
        │
        ▼
 You confirm ──► write <year>/hsa_data_<year>.json
        │
        ▼
 Review page (you): status, notes, reimbursed ──► auto-save, Export CSV, Claim report
```

## Quick start

0. Not sure where you are? Run `python tools/hsa.py status`. It lists each step as done or not and names the next one.
1. Open a terminal in this folder and start your LLM agent. Paste:

   > Read `AGENTS.md` to set up the Python environment, register the `amazon-orders-mcp` server, create the current year's folder from the example files, and guide me through my first order pull.

2. Sign in to Amazon once when prompted.
3. Double-click `review.html` in Chrome or Edge and choose your data folder when asked. (Other browsers: `python tools/hsa.py open`.) To try it on fake data first, choose the `samples` folder.

## Skills: task guides for any LLM agent

A skill is a short Markdown guide, `skills/<name>/SKILL.md`, that tells an agent how to do one job safely. Skills are plain text and name only commands and MCP tool names, so any agent can use them. The safety rules (your approval, steady pacing, the one-hour sign-in check, backups, stopping on a sign-in page) are enforced by the code. A skill explains them and calls them; it does not replace them.

**Install.** Nothing to install in Python: skills only call what setup already installed.

- Claude Code: copy each `skills/<name>/` folder into `.claude/skills/` (this project) or `~/.claude/skills/` (all projects). Then type `/amazon-live-batch`, or just describe the job. Copying always works. Linking instead keeps one copy up to date, but on Windows it needs Developer Mode or administrator rights (`mklink /J`); on macOS or Linux use `ln -s`.
- Other agents (Codex, Gemini CLI, Cursor, a local model): they read `AGENTS.md`. Say "Read `skills/amazon-live-batch/SKILL.md` and follow it", or copy the folder to wherever that agent keeps skills.

**Use.** Say what you want in plain words, for example "Re-check the product categories for 2026". The agent finds the matching skill, tells you how many pages it will load and about how long that takes, and waits for your yes before it contacts Amazon.

| Skill | Use it when | Status |
|---|---|---|
| `hsa-review` | **Start here.** "Open my HSA review": checks where you are, guides the next step, opens the page | Available |
| `amazon-live-batch` | Pulling or re-checking orders, or reading product pages | Available |
| `hsa-setup` | First run, or a new computer | Available |
| `hsa-categorize` | New product IDs need a category | Available |
| `hsa-reports` | Building the claim report, Deductible evidence PDF, or CSV | Available |
| `hsa-organize-files` | New PDFs or images need sorting into the year folder | Available |
| `hsa-medical-receipts`, `hsa-new-year`, `hsa-check` | Adding bills, starting a year, checking before you share | Planned |

Planned skills are written only after you approve each description.

## Credits and license

The Amazon orders MCP server is based on seanoliver/amazon-orders-mcp (MIT License). It lives in `mcp/amazon-orders/` and keeps its original `LICENSE`. The rest of this repository is under the MIT License in `LICENSE`.

## Privacy

Receipts, order data, decisions, cookies, and exports stay on your computer, in your data folder outside this code folder, so they cannot be committed by mistake. The `.gitignore` is a second layer. Run `python tools/check_personal_data.py` before you commit or share.
