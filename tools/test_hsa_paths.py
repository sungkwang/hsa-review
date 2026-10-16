"""Tests for the data-folder lookup and the local launcher. No real data, no Amazon contact.

Run:  python tools/test_hsa_paths.py
"""

import http.client
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hsa_paths import DataDirError, NOT_SET, data_dir, default_data_dir, write_config  # noqa: E402
from open_review import make_server  # noqa: E402


def test_order_is_cli_then_environment_then_config(tmp_path):
    cli, env, cfg = (tmp_path / n for n in ("cli", "env", "cfg"))
    for p in (cli, env, cfg):
        p.mkdir()
    config = tmp_path / "config.json"
    write_config(cfg, config)
    assert data_dir(str(cli), {"HSA_DATA_DIR": str(env)}, config) == cli.resolve()
    assert data_dir(None, {"HSA_DATA_DIR": str(env)}, config) == env.resolve()
    assert data_dir(None, {}, config) == cfg.resolve()


def test_nothing_set_stops_and_never_falls_back_to_the_code_folder(tmp_path):
    with pytest.raises(DataDirError) as e:
        data_dir(None, {}, tmp_path / "missing.json")
    assert str(e.value) == NOT_SET


def test_a_folder_that_does_not_exist_is_reported(tmp_path):
    with pytest.raises(DataDirError, match="does not exist"):
        data_dir(str(tmp_path / "nope"), {}, tmp_path / "missing.json")


def test_default_data_folder_is_named_hsa_review():
    assert default_data_dir().name == "HSA-Review"


@pytest.fixture()
def served(tmp_path):
    (tmp_path / "2026").mkdir()
    (tmp_path / "2026" / "hsa_data_2026.json").write_text("{}", encoding="utf-8")
    server = make_server(tmp_path, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()


def fetch(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    status = conn.getresponse().status
    conn.close()
    return status


def test_launcher_serves_the_page_and_the_data_folder_only(served):
    assert fetch(served, "/review.html") == 200
    assert fetch(served, "/data/2026/hsa_data_2026.json") == 200
    assert fetch(served, "/AGENTS.md") == 404  # the rest of the code folder is not served
    assert fetch(served, "/data/") == 404  # no folder listing
    assert fetch(served, "/data/..%2f..%2fAGENTS.md") == 404  # cannot climb out of the data folder
    assert fetch(served, "/data/%2e%2e/review.html") == 404


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", "--tb=short", "-p", "no:cacheprovider", __file__]))
