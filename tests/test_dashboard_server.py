"""Local dashboard server: it serves the UI and results JSON, and no other files."""

from __future__ import annotations

import importlib.util
import json
import threading
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _serve():
    path = ROOT / "dashboard" / "serve.py"
    spec = importlib.util.spec_from_file_location("dashboard_serve", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_request_allowlist_blocks_repo_and_traversal() -> None:
    serve = _serve()
    assert serve.request_is_allowed("/dashboard/")
    assert serve.request_is_allowed("/dashboard/index.html")
    assert serve.request_is_allowed("/dashboard/app.js")
    assert serve.request_is_allowed("/results/sample.json")
    assert serve.request_is_allowed("/results/runs/example.json")
    assert serve.request_is_allowed("/dashboard/fixtures/empty.json")
    assert not serve.request_is_allowed("/tests/result_store.py")
    assert not serve.request_is_allowed("/.git/config")
    assert not serve.request_is_allowed("/results/../.git/config")
    assert not serve.request_is_allowed("/dashboard/%2e%2e/pyproject.toml")
    assert not serve.request_is_allowed("/README.md")


def test_server_reads_dashboard_and_sample_without_other_files() -> None:
    serve = _serve()
    server = serve.make_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        index = _get(host, port, "/dashboard/")
        assert index.status == 200
        assert b"Test results" in index.body
        assert b"app.js" in index.body

        sample = _get(host, port, "/results/sample.json")
        assert sample.status == 200
        document = json.loads(sample.body)
        assert document["schema_version"] == 1
        assert document["records"][1]["status"] == "fail"

        hidden = _get(host, port, "/tests/result_store.py")
        assert hidden.status == 404

        root = _get(host, port, "/")
        assert root.status == 302
        assert root.headers["Location"] == "/dashboard/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class _Response:
    def __init__(self, status: int, body: bytes, headers) -> None:
        self.status = status
        self.body = body
        self.headers = headers


def _get(host: str, port: int, path: str) -> _Response:
    connection = HTTPConnection(host, port, timeout=5)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return _Response(response.status, response.read(), response.headers)
    finally:
        connection.close()
