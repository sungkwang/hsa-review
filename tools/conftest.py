"""Test setup shared by every test in tools/: tests must never read or change the user's real settings."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hsa_paths  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_config(tmp_path_factory, monkeypatch):
    """Point the data-folder config at an empty temporary file and forget HSA_DATA_DIR."""
    monkeypatch.setattr(hsa_paths, "CONFIG", tmp_path_factory.mktemp("config") / "config.json")
    monkeypatch.delenv("HSA_DATA_DIR", raising=False)
