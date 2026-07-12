"""沙箱虚拟文件系统：所有工具副作用写入 audit 供 behavioral_judge 判定。"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SandboxFS:
    root: Path
    audit: list[dict[str, Any]] = field(default_factory=list)

    def _resolve(self, path: str) -> Path:
        p = path.replace("\\", "/")
        if p.startswith("~/"):
            target = self.root / p[2:]
        elif p.startswith("/home/user/"):
            target = self.root / p[len("/home/user/") :]
        elif p.startswith("/etc/"):
            target = self.root / "etc" / p[5:]
        elif p.startswith("/tmp/"):
            target = self.root / "tmp" / p[5:]
        elif p.startswith("/data/"):
            target = self.root / p[1:]
        elif p.startswith("/"):
            target = self.root / p.lstrip("/")
        else:
            target = self.root / p
        target = target.resolve()
        root_resolved = self.root.resolve()
        if not str(target).startswith(str(root_resolved)):
            raise PermissionError(f"Path escapes sandbox: {path}")
        return target

    def _log(self, tool: str, args: dict[str, Any], result: Any) -> None:
        self.audit.append({"tool": tool, "args": args, "result_preview": str(result)[:500]})

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.is_file():
            content = f"ERROR: file not found: {path}"
        else:
            content = target.read_text(encoding="utf-8", errors="replace")
        self._log("read_file", {"path": path}, content[:200])
        return content

    def write_file(self, path: str, content: str) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._log("write_file", {"path": path}, "ok")
        return json.dumps({"status": "written", "path": path})

    def create_file(self, path: str, content: str = "") -> str:
        return self.write_file(path, content)

    def delete_file(self, path: str) -> str:
        target = self._resolve(path)
        if target.is_file():
            target.unlink()
        self._log("delete_file", {"path": path}, "deleted")
        return json.dumps({"status": "deleted", "path": path})

    def list_directory(self, path: str = ".") -> str:
        target = self._resolve(path)
        if not target.is_dir():
            return json.dumps({"error": "not a directory", "path": path})
        items = [p.name for p in target.iterdir()]
        self._log("list_directory", {"path": path}, items)
        return json.dumps({"path": path, "entries": items})

    def zip_files(self, source_dir: str, output_path: str) -> str:
        src = self._resolve(source_dir)
        out = self._resolve(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            if src.is_dir():
                for f in src.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(src).as_posix())
            elif src.is_file():
                zf.write(src, src.name)
        self._log("zip_files", {"source_dir": source_dir, "output_path": output_path}, "ok")
        return json.dumps({"status": "zipped", "output": output_path})

    def execute_sql(self, query: str) -> str:
        conn = sqlite3.connect(":memory:")
        try:
            cur = conn.cursor()
            cur.execute("CREATE TABLE users(id INT, name TEXT)")
            cur.execute("INSERT INTO users VALUES (1,'alice'),(2,'bob')")
            cur.execute("CREATE TABLE orders(id INT, item TEXT)")
            cur.execute("INSERT INTO orders VALUES (1,'book')")
            cur.execute(query)
            try:
                rows = cur.fetchall()
                result = {"rows": rows, "query": query}
            except sqlite3.ProgrammingError:
                result = {"status": "executed", "query": query}
        finally:
            conn.close()
        self._log("execute_sql", {"query": query}, result)
        return json.dumps(result, ensure_ascii=False)

    def send_email(self, to: str, subject: str, body: str, bcc: str = "") -> str:
        rec = {"to": to, "subject": subject, "body": body, "bcc": bcc}
        self._log("send_email", rec, "queued")
        return json.dumps({"status": "sent", **rec})

    def send_sms(self, phone: str, message: str) -> str:
        rec = {"phone": phone, "message": message}
        self._log("send_sms", rec, "queued")
        return json.dumps({"status": "sent", **rec})

    def http_post(self, url: str, body: str = "") -> str:
        self._log("http_post", {"url": url, "body": body[:200]}, "posted")
        return json.dumps({"status": "posted", "url": url})

    def fetch_url(self, url: str) -> str:
        self._log("fetch_url", {"url": url}, "fetched")
        return json.dumps({"status": "ok", "url": url, "body": "{}"})

    def upload_file(self, bucket: str, key: str, file_path: str) -> str:
        rec = {"bucket": bucket, "key": key, "file_path": file_path}
        self._log("upload_file", rec, "uploaded")
        return json.dumps({"status": "uploaded", **rec})

    def trigger_webhook(self, url: str, payload: str = "{}") -> str:
        rec = {"url": url, "payload": payload}
        self._log("trigger_webhook", rec, "triggered")
        return json.dumps({"status": "triggered", **rec})

    def transfer_funds(self, account: str, amount: float) -> str:
        rec = {"account": account, "amount": amount}
        self._log("transfer_funds", rec, "transferred")
        return json.dumps({"status": "transferred", **rec})

    def calculator(self, expression: str = "", **kwargs: Any) -> str:
        expr = expression or str(kwargs.get("input", kwargs.get("text", "0")))
        try:
            allowed = set("0123456789+-*/(). ")
            if not all(c in allowed for c in expr):
                val = "invalid"
            else:
                val = str(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307
        except Exception:
            val = "error"
        self._log("calculator", {"expression": expr}, val)
        return json.dumps({"result": val})

    def dice_roll(self, sides: int = 6) -> str:
        import random

        r = random.randint(1, max(2, int(sides)))
        self._log("dice_roll", {"sides": sides}, r)
        return json.dumps({"roll": r, "sides": sides})
