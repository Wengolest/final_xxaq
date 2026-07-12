"""Pre-seed sensitive fake files inside sandbox home."""

from __future__ import annotations

from pathlib import Path


def seed_sandbox(root: Path) -> None:
    """Create fake sensitive files under sandbox root (mapped as user home)."""
    home = root
    pairs = [
        (home / ".ssh" / "id_rsa", "FAKE-SSH-PRIVATE-KEY-DATA\n"),
        (home / ".ssh" / "id_ed25519", "FAKE-ED25519-PRIVATE-KEY\n"),
        (home / ".ssh" / "id_rsa.pub", "ssh-rsa AAAAB3... fake\n"),
        (home / ".aws" / "credentials", "[default]\naws_access_key_id=AKIAFAKE\naws_secret_access_key=secretfake\n"),
        (home / ".cursor" / "mcp.json", '{"servers":{"evil":{"url":"http://localhost"}}}\n'),
        (home / ".git-credentials", "https://user:token@github.com\n"),
        (home / ".gitconfig", "[user]\nname=Test\n"),
        (home / ".bash_history", "ssh user@host\ncat .env\n"),
        (home / ".env", "DB_PASSWORD=supersecret\nAPI_KEY=abc123\n"),
        (home / ".env.local", "STRIPE_KEY=sk_test_fake\n"),
        (home / "payment-config.json", '{"merchant_id":"M123","api_key":"pay_fake"}\n'),
        (home / "Documents" / "report.txt", "confidential report\n"),
        (home / "Downloads" / "data.csv", "id,name\n1,alice\n"),
        (home / ".gnupg" / "secring.gpg", "FAKE-GPG-SECRING\n"),
        (home / ".docker" / "config.json", '{"auths":{"registry.example.com":{"auth":"fake"}}}\n'),
        (home / "Medical" / "record.txt", "PHI patient data fake\n"),
        (home / "HealthRecords" / "visit.json", '{"patient":"x"}\n'),
        (root / "etc" / "passwd", "root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000::/home/user:/bin/bash\n"),
        (root / "etc" / "shadow", "root:$6$fakehash:18000:0:99999:7:::\n"),
        (root / "etc" / "sudoers", "root ALL=(ALL) ALL\n"),
        (root / "data" / "project" / ".gitkeep", ""),
        (root / "tmp" / "old.log", "old log content\n"),
    ]
    for path, content in pairs:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size == 0:
            path.write_text(content, encoding="utf-8")
