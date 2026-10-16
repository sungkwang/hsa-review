---
name: hsa-review
description: Use when the user says "open my HSA review", "start HSA review", "/hsa-review", or is unsure where they are in the HSA receipt review. Runs hsa status, guides the next unfinished step, otherwise opens the review page and lists what else the user can ask for. This is the front door; it routes to the other HSA skills.
---

# HSA review: the front door

For any LLM agent. Users remember one name; this skill routes to the others.

1. **Run** `python tools/hsa.py status` (add `--year <year>` if the user names one). It prints a checklist and names the next step.
2. **If a step is unchecked,** do only that step, in plain words, then run `status` again. Setup problems go to the `hsa-setup` skill. Every failure ends with "Next: ...": say that action to the user.
3. **If everything is checked,** tell the user to double-click `review.html` in Chrome or Edge (the first time it asks for their HSA-Review folder; after that one click on "Allow"). For Firefox or Safari, or if the user prefers, run `python tools/hsa.py open`: it starts the page on this computer only and prints the address; tell them to keep that window running while they use the page.
4. **Then offer what else they can ask for**, one short line each:
   - "Pull my 2026 Amazon orders" or "re-check my orders" → `amazon-live-batch` (shows the page count and time, asks first).
   - "Find categories for my products" → `hsa-categorize`.
   - "Sort my new PDFs" → `hsa-organize-files`.
   - "Make my claim report" or "make the Deductible evidence PDF" → `hsa-reports`.
   - "Set up on a new computer" → `hsa-setup`.

People who do not use an agent can simply double-click `review.html`. The **HSA Review** desktop shortcut (setup offers it; `python tools/hsa.py shortcut` makes it later) is the fallback for browsers without folder access.

Rules: no live Amazon request without the user's yes; never decide eligibility for the user; user data stays in the data folder, outside this code folder.
