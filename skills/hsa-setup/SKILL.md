---
name: hsa-setup
description: Use when setting up HSA receipt review for the first time or on a new computer. Asks for the year and data folder, installs packages and the Amazon MCP server, shows the MCP config for your agent (writes it only if you confirm), and runs the checks once.
---

# HSA setup

For any LLM agent. Follow `AGENTS.md` "One-time setup"; this skill is the order and the checks.

**Start with `python tools/hsa.py status`.** It checks what is already done and names the next step. Guide the user through the first unchecked step, one at a time, then run `status` again. `python tools/hsa.py setup` does the early steps (prerequisites, data folder, year folder from the templates) and stops with "Next: ..." if one fails. The steps below are the detail behind each line of the checklist.

1. **Ask** which tax year, and where the user's data folder should be. Suggest `python tools/hsa_paths.py --suggest` (Documents/HSA-Review or ~/HSA-Review). It must be outside the code folder. Do not guess.
2. **Install:** Python 3.11 or 3.12; install the Amazon MCP server that ships in this repository: from the repository folder run `pip install -e mcp/amazon-orders` and `python -m playwright install chromium`.
3. **MCP config:** print the contents of `.mcp.json.example` adapted to the user's agent. Write the file only after the user says yes. Never overwrite an existing config; show the difference instead.
4. **Data folder:** save it with `python tools/hsa_paths.py --set <folder>`. `python tools/hsa.py setup --year <year>` then creates `<year>/receipts/`, `reports/`, `decisions.json` (from `templates/hsa_decisions_example.json`) and `_app/` with `data.json` (from `templates/hsa_data_example.json`).
5. **Sign in once** with the `refresh_session` tool (or `python cookie_capture.py` in the MCP folder). The user types the password and any 2-step code.
6. **Check:** `python tools/test_review_page.py` (every check PASSED) and `python tools/check_personal_data.py` (clean). Report what failed, if anything.
7. **Open** the page: tell the user to double-click `review.html` in Chrome or Edge and choose the data folder once (other browsers: `python tools/hsa.py open`). To try the page on fake data first, choose the `samples` folder.

Rules: no live Amazon request without the user's yes; user data stays outside the code folder; never commit year folders, images, cookies, or `.mcp.json`.
