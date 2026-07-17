"""Mock web server for web-based attack scenarios."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Callable


class _StaticHandler(BaseHTTPRequestHandler):
    content_map: dict[str, str] = {}

    def log_message(self, format: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/":
            path = "/index.html"
        content = self.content_map.get(path)
        if content is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MockWebServer:
    """Serve attack pages locally for web redirect / web single scenarios."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.routes: dict[str, str] = {}

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def add_route(self, path: str, content: str) -> None:
        if not path.startswith("/"):
            path = f"/{path}"
        self.routes[path] = content

    def add_file(self, path: str, file_path: Path) -> None:
        self.add_route(path, file_path.read_text(encoding="utf-8"))

    def start(self) -> None:
        _StaticHandler.content_map = self.routes
        self._server = HTTPServer((self.host, self.port), _StaticHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None

    def __enter__(self) -> MockWebServer:
        self.start()
        return self

    def __exit__(self, *args: Callable) -> None:
        self.stop()
