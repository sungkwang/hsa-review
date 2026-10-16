---
name: hsa-organize-files
description: Use when new PDFs or images (Amazon orders, medical bills, receipts, insurance statements, doctor's notes) need to be named and filed in the year's receipts folder. Names each file YYYY-MM-DD_type_source_detail with a type of order, bill, receipt, eob, or letter; shows a table first, changes nothing until you confirm, never deletes, keeps an undo log, skips duplicates by file hash, and leaves unidentified files with their names.
---

# Organize documents

The command does the work; this skill is how to run it safely. All documents go in one flat folder, `<data folder>/<year>/receipts/` (the data folder comes from `--data-dir`, `HSA_DATA_DIR`, or the setup config), and the name says what each file is: `date_type_source_detail`, for example `2026-08-12_bill_ENT-clinic_visit.pdf`.

1. **Ask** which folder holds the new files (Downloads, a scanner folder), or whether the files are already in `receipts/`. Do not look elsewhere.
2. **Plan only:** `python tools/organize_files.py <folder> --year <year>` moves new files in; `python tools/organize_files.py --year <year>` renames what is already in `receipts/`. It prints one line per file: old name, new path, and a note. Nothing is changed.
3. **Show the user the table.** Point out files that stay unidentified (with the reason), duplicates left in place, and files whose document year differs from the download year.
4. **Wait for a yes.** Then run the same command with `--confirm`. Files are moved or renamed, never deleted, and the run is logged in `<year>/_app/logs/`.
5. **Undo** with `python tools/organize_files.py --undo` if the user changes their mind.
6. **Check:** `python tools/hsa.py status` (it lists any file still "not identified") and `python tools/check_evidence.py <year>`.

What the command decides: the type, from the PDF's text layer (order, bill, receipt, eob, letter); the date from the document, not the download; duplicates by file hash, not by name.

What it does not do: read images or scans. They keep their names; the user can rename them by hand (`2026-08-14_receipt_pharmacy.png`) or, only if they agree, have a model read one (a local model keeps it on the computer), and say so. Never guess a type, date, or provider.
