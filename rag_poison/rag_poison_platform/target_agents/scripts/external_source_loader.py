"""Load simulated external source markdown files for supply-chain experiments."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.paths import EXTERNAL_SOURCES_DIR

TARGET_POISON_MAP = {
    "websearch_external_content_risk": "fake_official_faq_websearch.md",
    "fileupload_prompt_injection_risk": "fake_release_note_fileupload.md",
    "plugin_result_tampering_risk": "fake_vendor_advisory_plugin.md",
}

DEFAULT_POISON_FILE = "generic_fake_security_advisory.md"


def _parse_header_metadata(text: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    for line in text.splitlines()[:12]:
        m = re.match(r"^([a-z_]+):\s*(.+)$", line.strip())
        if m:
            key, val = m.group(1), m.group(2).strip()
            if key in {
                "external_source_url",
                "source_type",
                "domain",
                "trust_level",
                "fetched_at",
            }:
                meta[key] = val
    return meta


def _load_dir(subdir: str) -> List[Dict[str, Any]]:
    root = EXTERNAL_SOURCES_DIR / subdir
    docs: List[Dict[str, Any]] = []
    if not root.is_dir():
        return docs
    for path in sorted(root.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta = _parse_header_metadata(text)
        meta["external_source"] = True
        meta["origin_dir"] = subdir
        docs.append(
            {
                "doc_id": f"ext_{subdir}_{path.stem}",
                "content": text,
                "metadata": meta,
            }
        )
    return docs


def load_clean_external_docs() -> List[Dict[str, Any]]:
    return _load_dir("clean_web")


def load_poisoned_external_docs() -> List[Dict[str, Any]]:
    return _load_dir("poisoned_web")


def select_poison_doc_for_target(
    target_id: str,
    poisoned_docs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    pool = poisoned_docs or load_poisoned_external_docs()
    filename = TARGET_POISON_MAP.get(target_id, DEFAULT_POISON_FILE)
    for doc in pool:
        if doc["doc_id"].endswith(Path(filename).stem):
            return doc
    for doc in pool:
        if DEFAULT_POISON_FILE.replace(".md", "") in doc["doc_id"]:
            return doc
    if pool:
        return pool[0]
    raise FileNotFoundError(f"No poisoned external doc for target {target_id}")
