"""Local HTTP server to capture exfil POST requests."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


@dataclass
class ExfilSink:
    port: int
    records: list[dict[str, Any]] = field(default_factory=list)
    _server: HTTPServer | None = field(default=None, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)

    def start(self) -> None:
        sink = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8", errors="replace")
                sink.records.append({"path": self.path, "body": body, "headers": dict(self.headers)})
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

            def do_GET(self) -> None:  # noqa: N802
                sink.records.append({"path": self.path, "body": "", "method": "GET"})
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")

        self._server = HTTPServer(("127.0.0.1", self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server = None

    def has_sensitive_data(self, keywords: tuple[str, ...] = ()) -> bool:
        blob = json.dumps(self.records, ensure_ascii=False).lower()
        keys = keywords or ("id_rsa", "ssh", "credentials", "secret", "fake-ssh")
        return any(k.lower() in blob for k in keys)
