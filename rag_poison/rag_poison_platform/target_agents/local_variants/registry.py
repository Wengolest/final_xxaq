"""Local RAG variant definitions (not external GitHub agents)."""

from __future__ import annotations

from typing import Any, Dict, List

# Ports 18201+; harness stays on 18100. Each variant reuses minimal_http_rag_agent app.
LOCAL_VARIANT_BASE_PORT = 18201

RETRIEVER_PROFILES = [
    "tfidf_top5",
    "tfidf_top10",
    "keyword_overlap_top5",
    "trusted_source_boost_top5",
    "poison_boost_top5",
    "poison_boost_top10",
    "clean_demotion_top5",
    "poison_top1_forced",
]


def build_local_variants(*, include_deepseek: bool = True) -> List[Dict[str, Any]]:
    """Generate local_variant entries for sample pool (>=16 base, up to 20 with extras)."""
    variants: List[Dict[str, Any]] = []
    port = LOCAL_VARIANT_BASE_PORT

    for profile in RETRIEVER_PROFILES:
        variants.append(
            {
                "agent_id": f"local_rag_mock_{profile}",
                "sample_type": "local_variant",
                "local_variant": True,
                "model_backend": "mock",
                "default_retriever_profile": profile,
                "api_base_url": f"http://127.0.0.1:{port}",
                "assigned_port": port,
                "poison_test_supported": True,
                "repo_url": "platform:local_variant/minimal_http_rag_agent",
                "notes": "mock LLM via empty key + heuristic fallback",
            }
        )
        port += 1

    if include_deepseek:
        for profile in RETRIEVER_PROFILES:
            variants.append(
                {
                    "agent_id": f"local_rag_deepseek_{profile}",
                    "sample_type": "local_variant",
                    "local_variant": True,
                    "model_backend": "deepseek",
                    "default_retriever_profile": profile,
                    "api_base_url": f"http://127.0.0.1:{port}",
                    "assigned_port": port,
                    "poison_test_supported": True,
                    "repo_url": "platform:local_variant/minimal_http_rag_agent",
                    "notes": "DeepSeek via OPENAI-compat env mapping",
                }
            )
            port += 1

    # Extra mock variants to reach >=20 pool entries standalone
    extras = [
        ("local_rag_mock_harness_alias", "tfidf_top5", "alias of harness for pool counting"),
        ("local_rag_mock_metadata_filter", "trusted_source_boost_top5", "metadata_filter smoke"),
        ("local_rag_mock_fallback", "keyword_overlap_top5", "allow_fallback smoke"),
        ("local_rag_mock_forced_poison", "poison_top1_forced", "forced poison rank"),
    ]
    for agent_id, profile, note in extras:
        variants.append(
            {
                "agent_id": agent_id,
                "sample_type": "local_variant",
                "local_variant": True,
                "model_backend": "mock",
                "default_retriever_profile": profile,
                "api_base_url": f"http://127.0.0.1:{port}",
                "assigned_port": port,
                "poison_test_supported": True,
                "repo_url": "platform:local_variant/minimal_http_rag_agent",
                "notes": note,
            }
        )
        port += 1

    return variants
