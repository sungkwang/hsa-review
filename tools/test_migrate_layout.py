"""Tests for migrate_layout.py on a fake data folder. No real data, no Amazon contact.

Run:  python tools/test_migrate_layout.py
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import migrate_layout  # noqa: E402
from hsa_paths import year_paths  # noqa: E402


@pytest.fixture()
def old_folder(tmp_path):
    root = tmp_path / "HSA-Review"
    y = root / "2026"
    (y / "backups" / "2026-10-15").mkdir(parents=True)
    (root / "images").mkdir()
    (root / "images" / "a.jpg").write_bytes(b"jpg")
    (y / "backups" / "2026-10-15" / "old.json").write_text("{}", encoding="utf-8")
    data = {"MEDICAL": [{"id": "MED|1", "src": "visit.pdf", "provider": "Sample ENT Clinic", "date": "2026-06-09", "thumb": "images/a.jpg"}], "ORDERS": []}
    (y / "hsa_data_2026.json").write_text(json.dumps(data), encoding="utf-8")
    (y / "hsa_decisions_2026.json").write_text('{"a|0": {"status": "Eligible"}}', encoding="utf-8")
    (y / "asin_info_2026.json").write_text("{}", encoding="utf-8")
    (y / "product_decisions_2026.json").write_text("{}", encoding="utf-8")
    (y / "2026-01-01_900-0000001-0000001_Invoice.pdf").write_bytes(b"%PDF-fake-invoice")
    (y / "visit.pdf").write_bytes(b"%PDF-fake-visit")
    (y / "amazon_hsa_decisions_2026.csv").write_text("a,b\n", encoding="utf-8")
    return root


def files(root):
    return sorted(p.relative_to(root).as_posix() for p in Path(root).rglob("*") if p.is_file())


def test_plan_changes_nothing_and_lists_old_and_new(old_folder, capsys):
    before = files(old_folder)
    assert migrate_layout.main(["--data-dir", str(old_folder)]) == 0
    out = capsys.readouterr().out
    assert files(old_folder) == before and not old_folder.with_name("HSA-Review.backup-x").exists()
    assert "hsa_data_2026.json  ->  2026/_app/data.json" in out
    assert "2026-01-01_900-0000001-0000001_Invoice.pdf  ->  2026/receipts/2026-01-01_order_amazon_900-0000001-0000001.pdf" in out
    assert "plan only" in out


def test_confirm_backs_up_checks_it_and_moves_everything(old_folder):
    backup = old_folder.with_name("HSA-Review.backup-test")
    before = files(old_folder)
    done, used = migrate_layout.migrate(old_folder, backup)
    assert used == backup and files(backup) == before  # the backup is a complete copy of the old folder
    got = files(old_folder)
    for expected in [
        "2026/_app/data.json", "2026/_app/README.txt", "2026/_app/product_cache.json", "2026/_app/product_decisions.json", "2026/_app/images/a.jpg",
        "2026/_app/backups/2026-10-15/old.json", "2026/decisions.json",
        "2026/reports/amazon_hsa_decisions_2026.csv",
        "2026/receipts/2026-01-01_order_amazon_900-0000001-0000001.pdf",
        "2026/receipts/2026-06-09_bill_Sample-ENT-Clinic_visit.pdf",
    ]:
        assert expected in got, expected
    assert not any(g.startswith("images/") or g == "2026/hsa_data_2026.json" for g in got)
    data = json.loads((old_folder / "2026" / "_app" / "data.json").read_text(encoding="utf-8"))
    assert data["MEDICAL"][0]["src"] == "2026-06-09_bill_Sample-ENT-Clinic_visit.pdf"  # data.json follows the rename
    paths = year_paths(old_folder, "2026")
    assert paths.new_layout and paths.data.exists() and paths.decisions.exists() and paths.images.is_dir()


def test_an_existing_backup_folder_stops_the_move(old_folder):
    backup = old_folder.with_name("HSA-Review.backup-test")
    backup.mkdir()
    before = files(old_folder)
    with pytest.raises(SystemExit):
        migrate_layout.migrate(old_folder, backup)
    assert files(old_folder) == before


def test_a_backup_that_differs_stops_the_move(old_folder, monkeypatch):
    monkeypatch.setattr(migrate_layout, "verify_copy", lambda a, b: ["differs: 2026/visit.pdf"])
    before = files(old_folder)
    with pytest.raises(SystemExit):
        migrate_layout.migrate(old_folder, old_folder.with_name("HSA-Review.backup-test"))
    assert files(old_folder) == before


def test_a_folder_already_in_the_new_layout_is_left_alone(old_folder):
    migrate_layout.migrate(old_folder, old_folder.with_name("HSA-Review.backup-test"))
    after_first = files(old_folder)
    assert migrate_layout.plan(old_folder) == ([], [])
    assert files(old_folder) == after_first


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "--tb=short", "-p", "no:cacheprovider", __file__]))
