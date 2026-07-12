"""Benign MCP tool definitions and dispatch handlers."""

from __future__ import annotations

import json
from typing import Any

from .sandbox.filesystem import SandboxFS

BENIGN_TOOL_DEFS: dict[str, dict[str, Any]] = {
    "read_file": {
        "name": "read_file",
        "description": "Read a file from the filesystem.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
    },
    "write_file": {
        "name": "write_file",
        "description": "Write content to a file.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    "create_file": {
        "name": "create_file",
        "description": "Create a new file with optional content.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path"],
        },
    },
    "delete_file": {
        "name": "delete_file",
        "description": "Delete a file.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    "list_directory": {
        "name": "list_directory",
        "description": "List directory entries.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    },
    "send_email": {
        "name": "send_email",
        "description": "Send an email message.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "bcc": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    "send_sms": {
        "name": "send_sms",
        "description": "Send an SMS message.",
        "inputSchema": {
            "type": "object",
            "properties": {"phone": {"type": "string"}, "message": {"type": "string"}},
            "required": ["phone", "message"],
        },
    },
    "http_post": {
        "name": "http_post",
        "description": "POST data to a URL.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}, "body": {"type": "string"}},
            "required": ["url"],
        },
    },
    "fetch_url": {
        "name": "fetch_url",
        "description": "Fetch content from a URL.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    "execute_sql": {
        "name": "execute_sql",
        "description": "Execute a SQL query against the demo database.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    "upload_file": {
        "name": "upload_file",
        "description": "Upload a file to cloud storage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bucket": {"type": "string"},
                "key": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["bucket", "key"],
        },
    },
    "trigger_webhook": {
        "name": "trigger_webhook",
        "description": "Trigger a webhook endpoint.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}, "payload": {"type": "string"}},
            "required": ["url"],
        },
    },
    "transfer_funds": {
        "name": "transfer_funds",
        "description": "Transfer funds to an account.",
        "inputSchema": {
            "type": "object",
            "properties": {"account": {"type": "string"}, "amount": {"type": "number"}},
            "required": ["account", "amount"],
        },
    },
    "zip_files": {
        "name": "zip_files",
        "description": "Zip files in a directory.",
        "inputSchema": {
            "type": "object",
            "properties": {"source_dir": {"type": "string"}, "output_path": {"type": "string"}},
            "required": ["source_dir", "output_path"],
        },
    },
    "calculator": {
        "name": "calculator",
        "description": "Evaluate a mathematical expression.",
        "inputSchema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
        },
    },
    "dice_roll": {
        "name": "dice_roll",
        "description": "Roll a dice with N sides.",
        "inputSchema": {
            "type": "object",
            "properties": {"sides": {"type": "integer", "default": 6}},
        },
    },
}


def normalize_tool_args(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Unwrap FastMCP/OpenAI nested kwargs so path/to/body reach handlers."""
    if not raw:
        return {}
    args = dict(raw)
    # OpenAI sometimes sends {"kwargs": "{\"path\": \"...\"}"} or {"kwargs": {...}}
    if "kwargs" in args:
        inner = args.pop("kwargs")
        if isinstance(inner, str):
            try:
                inner = json.loads(inner)
            except json.JSONDecodeError:
                # LLM 有时直接传路径字符串而非 JSON 对象
                if inner.startswith("~") or inner.startswith("/") or "\\" in inner:
                    inner = {"path": inner}
                else:
                    inner = {"input": inner}
        if isinstance(inner, dict):
            args = {**inner, **args}
    # expression/input aliases for calculator
    if "expression" not in args and "input" in args:
        args.setdefault("expression", args["input"])
    if "path" not in args and "file_path" in args:
        args.setdefault("path", args["file_path"])
    if "path" not in args and "filepath" in args:
        args.setdefault("path", args["filepath"])
    if "phone" not in args and "recipient" in args:
        args.setdefault("phone", args["recipient"])
    if "account" not in args and "payee_account" in args:
        args.setdefault("account", args["payee_account"])
    return args


def dispatch_tool(fs: SandboxFS, name: str, arguments: dict[str, Any]) -> str:
    """Route tools/call to sandbox handler."""
    args = normalize_tool_args(arguments)
    if name == "read_file":
        return fs.read_file(str(args.get("path", "")))
    if name == "write_file":
        return fs.write_file(str(args.get("path", "")), str(args.get("content", "")))
    if name == "create_file":
        return fs.create_file(str(args.get("path", "")), str(args.get("content", "")))
    if name == "delete_file":
        return fs.delete_file(str(args.get("path", "")))
    if name == "list_directory":
        return fs.list_directory(str(args.get("path", ".")))
    if name == "send_email":
        return fs.send_email(
            str(args.get("to", "")),
            str(args.get("subject", "")),
            str(args.get("body", "")),
            str(args.get("bcc", "")),
        )
    if name == "send_sms":
        return fs.send_sms(str(args.get("phone", args.get("recipient", ""))), str(args.get("message", "")))
    if name == "http_post":
        return fs.http_post(str(args.get("url", "")), str(args.get("body", "")))
    if name == "fetch_url":
        return fs.fetch_url(str(args.get("url", "")))
    if name == "execute_sql":
        return fs.execute_sql(str(args.get("query", "")))
    if name == "upload_file":
        return fs.upload_file(
            str(args.get("bucket", "")),
            str(args.get("key", "")),
            str(args.get("file_path", "")),
        )
    if name == "trigger_webhook":
        return fs.trigger_webhook(str(args.get("url", "")), str(args.get("payload", "{}")))
    if name == "transfer_funds":
        return fs.transfer_funds(str(args.get("account", args.get("payee_account", ""))), float(args.get("amount", 0)))
    if name == "zip_files":
        return fs.zip_files(str(args.get("source_dir", args.get("source", ""))), str(args.get("output_path", "")))
    if name == "calculator":
        return fs.calculator(str(args.get("expression", args.get("input", ""))))
    if name == "dice_roll":
        return fs.dice_roll(int(args.get("sides", 6)))
    if name in BENIGN_TOOL_DEFS:
        return json.dumps({"status": "executed", "tool": name, "received": args})
    return fs.calculator(**args)
