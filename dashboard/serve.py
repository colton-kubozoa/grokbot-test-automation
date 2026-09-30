#!/usr/bin/env python3
"""Serve the test-results dashboard on localhost.

Browsers block ``file://`` fetches of local JSON. This server exposes the
dashboard and the results JSON files, and nothing else in the repository.

    python dashboard/serve.py

Then open http://127.0.0.1:8765/dashboard/
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

_DASHBOARD_SUFFIXES = frozenset({".html", ".css", ".js", ".json"})
_LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})


def repo_root() -> Path:
    """Repository root that contains ``dashboard/`` and ``results/``."""
    return Path(__file__).resolve().parent.parent


def request_is_allowed(url_path: str) -> bool:
    """Return True when the URL is the dashboard, its assets, or a results JSON file."""
    parsed = urlsplit(url_path)
    if parsed.scheme or parsed.netloc:
        return False
    raw = unquote(parsed.path)
    if raw in ("", "/"):
        return True
    if "\\" in raw or "\x00" in raw:
        return False
    parts = [part for part in PurePosixPath(raw).parts if part not in ("/", "")]
    if not parts or any(part in {".", ".."} or part.startswith(".") for part in parts):
        return False
    if parts == ["dashboard"]:
        return True
    suffix = _suffix(parts[-1])
    if parts[0] == "dashboard" and suffix in _DASHBOARD_SUFFIXES:
        return True
    return parts[0] == "results" and suffix == ".json"


def _suffix(name: str) -> str:
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[1].lower()


class DashboardHandler(SimpleHTTPRequestHandler):
    """Read-only handler for dashboard assets and results JSON."""

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_HEAD(self) -> None:
        self._dispatch("HEAD")

    def _dispatch(self, method: str) -> None:
        path = urlsplit(self.path).path
        if path in ("", "/"):
            self.send_response(302)
            self.send_header("Location", "/dashboard/")
            self.end_headers()
            return
        if not request_is_allowed(self.path):
            self.send_error(404, "Not found")
            return
        if method == "HEAD":
            super().do_HEAD()
        else:
            super().do_GET()

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


class DashboardServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def make_server(host: str, port: int) -> DashboardServer:
    """Bind a loopback server rooted at the repository."""
    handler = partial(DashboardHandler, directory=str(repo_root()))
    return DashboardServer((host, port), handler)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Serve the test-results dashboard on localhost.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.host not in _LOOPBACK:
        raise SystemExit("Refusing to bind a non-loopback host.")
    server = make_server(args.host, args.port)
    bound_host, bound_port = server.server_address[:2]
    display_host = bound_host.decode() if isinstance(bound_host, bytes) else bound_host
    print(f"Dashboard: http://{display_host}:{bound_port}/dashboard/")
    print("Ctrl+C stops the server. The page only reads JSON.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
