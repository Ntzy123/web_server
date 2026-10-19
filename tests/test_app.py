"""应用与 TOML 工具的最小自检"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from web_server import app  # noqa: E402
from web_server import utils  # noqa: E402


def test_toml_roundtrip(tmp_path):
    path = str(tmp_path / "t.toml")
    data = {
        "water_token": "abc",
        "max_bytes": 2048,
        "enabled": True,
        "persons": [{"name": "张三", "project_code": "52010017"}],
    }
    utils.dump(data, path)
    with open(path, "rb") as f:
        assert b'[[persons]]' in f.read()
    assert utils.load(path) == data
    assert utils.load(str(tmp_path / "missing.toml")) is None


def test_routes_respond():
    client = app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/api/get_auth").data == b"OK"
    assert client.get("/api/nope").status_code == 404
