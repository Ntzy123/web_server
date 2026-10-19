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


def test_next_monday_midnight():
    from datetime import datetime
    from web_server.core import _next_monday_midnight

    # 周一 00:00:00 → 下周一（严格晚于当前时刻）
    assert _next_monday_midnight(datetime(2026, 10, 19)) == datetime(2026, 10, 26)
    # 周一中间 → 下周一
    assert _next_monday_midnight(datetime(2026, 10, 19, 10, 30)) == datetime(2026, 10, 26)
    # 周日 → 次日 00:00
    assert _next_monday_midnight(datetime(2026, 10, 18, 23, 59)) == datetime(2026, 10, 19)
