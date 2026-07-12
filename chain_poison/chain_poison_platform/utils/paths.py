"""Shared path constants for rag_poison_platform."""

from pathlib import Path

PLATFORM_ROOT = Path(__file__).resolve().parent.parent
AWESOME_ROOT = Path(r"D:\AI\Awesome-Rag-Attacks")

TARGETS_PATH = PLATFORM_ROOT / "targets" / "agent_security_targets.yaml"
CLEAN_CORPUS_DIR = PLATFORM_ROOT / "clean_corpus"
GENERATED_DIR = PLATFORM_ROOT / "generated" / "poison_docs"
RESULTS_DIR = PLATFORM_ROOT / "results"
RAG_CONFIG_PATH = PLATFORM_ROOT / "config" / "rag_config.yaml"
EXTERNAL_SOURCES_DIR = PLATFORM_ROOT / "external_sources"
