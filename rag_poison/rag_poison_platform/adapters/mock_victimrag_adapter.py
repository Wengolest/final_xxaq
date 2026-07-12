"""Mock VictimRAG backend adapter for local ASR experiments."""

import sys
import types
from typing import Any, Dict, List, Optional, Set

from langchain.schema import Document

from utils.corpus import load_clean_documents
from utils.paths import AWESOME_ROOT, RAG_CONFIG_PATH


def _ensure_awesome_import_path() -> None:
    awesome_str = str(AWESOME_ROOT)
    if awesome_str not in sys.path:
        sys.path.insert(0, awesome_str)
    # Awesome repo has src/*.py without __init__.py; register namespace package.
    if "src" not in sys.modules:
        src_pkg = types.ModuleType("src")
        src_pkg.__path__ = [str(AWESOME_ROOT / "src")]
        sys.modules["src"] = src_pkg


def _load_victim_rag():
    _ensure_awesome_import_path()
    from config.config import load_configuration
    from src.victim_rag import VictimRAG

    config = load_configuration(RAG_CONFIG_PATH)
    return VictimRAG(config.rag_config)


def _normalize_text(text: str) -> str:
    return " ".join(text.split()).strip()


class MockVictimRAGAdapter:
    """Build corpus from clean/poison docs and query VictimRAG."""

    _shared_rag = None

    def __init__(self, reuse_rag: bool = True):
        if reuse_rag and MockVictimRAGAdapter._shared_rag is not None:
            self.rag = MockVictimRAGAdapter._shared_rag
        else:
            self.rag = _load_victim_rag()
            MockVictimRAGAdapter._shared_rag = self.rag
        self.poison_signatures: Set[str] = set()
        self.poison_doc_ids: Set[str] = set()
        self._indexed = False

    def _register_poison_docs(self, poison_docs: List[Dict[str, Any]]) -> None:
        for doc in poison_docs:
            self.poison_signatures.add(_normalize_text(doc["content"]))
            self.poison_doc_ids.add(doc["doc_id"])

    def _select_corpus(
        self,
        clean_docs: List[Dict[str, Any]],
        poison_docs: List[Dict[str, Any]],
        corpus_mode: str,
    ) -> List[Dict[str, Any]]:
        if corpus_mode == "clean":
            return list(clean_docs)
        if corpus_mode == "poison_only":
            return list(poison_docs)
        if corpus_mode == "mixed":
            return list(clean_docs) + list(poison_docs)
        raise ValueError(f"Unknown corpus_mode: {corpus_mode}")

    def build_index(
        self,
        poison_docs: List[Dict[str, Any]],
        corpus_mode: str = "mixed",
    ) -> None:
        clean_docs = load_clean_documents()
        selected = self._select_corpus(clean_docs, poison_docs, corpus_mode)

        self.poison_signatures.clear()
        self.poison_doc_ids.clear()
        if corpus_mode in {"poison_only", "mixed"}:
            self._register_poison_docs(poison_docs)

        documents = []
        for item in selected:
            metadata = dict(item.get("metadata", {}))
            metadata.setdefault("doc_id", item["doc_id"])
            metadata.setdefault("is_poison", metadata.get("is_poison", False))
            documents.append(
                Document(page_content=item["content"], metadata=metadata)
            )

        processed = self.rag.prepare_documents(documents)
        self.rag.build_vectorstore(processed)
        self.rag.setup_retrieval_chain()
        self._indexed = True

    def _is_poison_content(self, content: str, metadata: Dict[str, Any]) -> bool:
        if metadata.get("is_poison"):
            return True
        normalized = _normalize_text(content)
        if normalized in self.poison_signatures:
            return True
        doc_id = metadata.get("doc_id")
        return bool(doc_id and doc_id in self.poison_doc_ids)

    def query(self, question: str) -> Dict[str, Any]:
        if not self._indexed:
            raise RuntimeError("Call build_index() before query().")

        result = self.rag.execute_retrieval_query(question)
        retrieved_sources = []
        poison_retrieved = False
        poison_rank: Optional[int] = None

        for rank, source in enumerate(result["source_documents"], start=1):
            content = source["content"]
            metadata = source.get("metadata", {})
            is_poison = self._is_poison_content(content, metadata)
            if is_poison and not poison_retrieved:
                poison_retrieved = True
                poison_rank = rank
            retrieved_sources.append(
                {
                    "rank": rank,
                    "content": content,
                    "metadata": metadata,
                    "is_poison": is_poison,
                }
            )

        return {
            "question": question,
            "answer": result["answer"],
            "retrieved_sources": retrieved_sources,
            "poison_retrieved": poison_retrieved,
            "poison_rank": poison_rank,
        }
