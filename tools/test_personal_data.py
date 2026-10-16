"""Personal-data scan tests. Offline; no Amazon contact."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_personal_data import scan  # noqa: E402


def test_repository_is_clean():
    assert scan(ROOT) == []


def test_detects_order_number(tmp_path):
    # Split so this test file doesn't contain an order-number pattern itself
    sample = "111-" + "8365921-4410207"  # not an obviously invented number (those are allowed on purpose)
    (tmp_path / "notes.md").write_text(f"Order {sample} was shipped.", encoding="utf-8")
    assert any("order number" in p for p in scan(tmp_path))


def test_detects_personal_file_names(tmp_path):
    (tmp_path / "2026").mkdir()
    (tmp_path / "2026" / "hsa_data_2026.json").write_text("", encoding="utf-8")
    (tmp_path / "receipt.pdf").write_bytes(b"%PDF")
    (tmp_path / "cookies.json").write_text("{}", encoding="utf-8")
    problems = scan(tmp_path)
    assert any("2026" in p for p in problems)
    assert any("receipt.pdf" in p for p in problems)
    assert any("cookies.json" in p for p in problems)


def test_detects_listed_personal_terms(tmp_path, monkeypatch):
    terms = tmp_path.parent / "terms.txt"
    terms.write_text("Example Person\n", encoding="utf-8")
    monkeypatch.setenv("HSA_PERSONAL_TERMS", str(terms))
    (tmp_path / "readme.md").write_text("Written for Example Person.", encoding="utf-8")
    assert any("personal term" in p for p in scan(tmp_path))


def test_template_files_are_allowed(tmp_path):
    (tmp_path / "template").mkdir()
    (tmp_path / "template" / "hsa_data_example.json").write_text("{}\n", encoding="utf-8")
    assert scan(tmp_path) == []


# --- samples/: PDFs and images are allowed by type; contents and metadata are still checked ---

def _sample_pdf(path, body):
    from make_samples import html_to_pdf

    html_to_pdf(f"<html><body>{body}</body></html>", path)


def test_marked_fake_sample_pdf_is_allowed(tmp_path):
    (tmp_path / "samples" / "2025").mkdir(parents=True)
    _sample_pdf(tmp_path / "samples" / "2025" / "2025-03-14_amazon_900-0000001-0000001.pdf", "<p>SAMPLE order 900-0000001-0000001, product BFAKE00001</p>")
    assert scan(tmp_path) == []


def test_sample_without_marker_or_with_a_real_order_number_fails(tmp_path):
    (tmp_path / "2025").mkdir()
    (tmp_path / "2025" / "hsa_data_2025.json").write_text('{"ORDERS": [{ "id":"900-2222222-3333333", "asin":"BREAL00001" }];', encoding="utf-8")
    (tmp_path / "samples").mkdir()
    _sample_pdf(tmp_path / "samples" / "a.pdf", "<p>no marker here</p>")
    _sample_pdf(tmp_path / "samples" / "b.pdf", "<p>SAMPLE 900-2222222-3333333 and BREAL00001</p>")
    found = " | ".join(scan(tmp_path))
    assert "a.pdf: no visible SAMPLE marker" in found
    assert "b.pdf: a real order number" in found and "b.pdf: a real product ID" in found


def test_sample_order_numbers_must_use_the_900_prefix(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "orders.csv").write_text("note,order\nSAMPLE," + "114" + "-0000000-0000000\n", encoding="utf-8")
    assert any("does not start with 900-" in p for p in scan(tmp_path))


def test_sample_pdf_metadata_fails(tmp_path):
    from pypdf import PdfReader, PdfWriter

    (tmp_path / "samples").mkdir()
    _sample_pdf(tmp_path / "samples" / "c.pdf", "<p>SAMPLE</p>")
    writer = PdfWriter(clone_from=PdfReader(tmp_path / "samples" / "c.pdf"))
    writer.add_metadata({"/Author": "Someone Real"})
    with open(tmp_path / "samples" / "c.pdf", "wb") as f:
        writer.write(f)
    assert any("metadata is not empty" in p for p in scan(tmp_path))


def test_a_year_folder_or_images_inside_the_code_folder_fails_even_if_ignored(tmp_path):
    (tmp_path / "2026").mkdir()
    (tmp_path / "images").mkdir()
    found = " | ".join(scan(tmp_path))
    assert "2026/: a year folder inside the code folder" in found
    assert "images/: user data inside the code folder" in found


def test_data_outside_the_code_folder_is_clean(tmp_path):
    (tmp_path / "code").mkdir()
    (tmp_path / "code" / "README.md").write_text("Nothing personal.", encoding="utf-8")
    (tmp_path / "data" / "2026").mkdir(parents=True)
    assert scan(tmp_path / "code") == []


def test_invented_order_numbers_and_a_license_with_the_authors_name_are_allowed(tmp_path, monkeypatch):
    terms = tmp_path / "terms.txt"
    terms.write_text("Example Person\n", encoding="utf-8")
    monkeypatch.setenv("HSA_PERSONAL_TERMS", str(terms))
    code = tmp_path / "code"  # the terms file stays outside the folder that is scanned
    code.mkdir()
    (code / "LICENSE").write_text("Copyright (c) 2026 Example Person\n", encoding="utf-8")
    (code / "test_x.py").write_text('ORDERS = ["111-0000000-0000001", "112-1234567-1234567", "111-2222222-3333333", "900-0000001-0000001"]\n', encoding="utf-8")
    assert scan(code) == []


def test_a_real_looking_order_number_or_a_name_in_a_readme_is_still_flagged(tmp_path, monkeypatch):
    terms = tmp_path / "terms.txt"
    terms.write_text("Example Person\n", encoding="utf-8")
    monkeypatch.setenv("HSA_PERSONAL_TERMS", str(terms))
    (tmp_path / "notes.md").write_text("Order " + "114" + "-8365921-" + "4410207" + " for Example Person\n", encoding="utf-8")
    found = " | ".join(scan(tmp_path))
    assert "Amazon order number" in found and "contains a personal term" in found
