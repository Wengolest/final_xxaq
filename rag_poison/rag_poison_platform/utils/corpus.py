"""Load clean corpus documents from disk."""

from pathlib import Path
from typing import Dict, List

from utils.paths import CLEAN_CORPUS_DIR


def list_clean_corpus_files(corpus_dir: Path = CLEAN_CORPUS_DIR) -> List[Path]:
    return sorted(corpus_dir.rglob("*.txt"))


def load_clean_documents(corpus_dir: Path = CLEAN_CORPUS_DIR) -> List[Dict]:
    documents = []
    for file_path in list_clean_corpus_files(corpus_dir):
        rel_path = file_path.relative_to(corpus_dir).as_posix()
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        documents.append(
            {
                "doc_id": rel_path.replace("/", "__"),
                "rel_path": rel_path,
                "content": content,
                "metadata": {
                    "source": "clean_corpus",
                    "rel_path": rel_path,
                    "is_poison": False,
                },
            }
        )
    return documents
