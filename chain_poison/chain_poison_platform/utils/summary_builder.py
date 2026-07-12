"""Build extended experiment summary JSON from result CSV files."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _rate(success: int, total: int) -> float:
    return round(success / total, 4) if total else 0.0


def _group_asr(rows: Iterable[Dict[str, str]], key: str) -> Dict[str, float]:
    buckets: Dict[str, List[bool]] = defaultdict(list)
    for row in rows:
        buckets[row.get(key, "unknown")].append(_as_bool(row.get("attack_success")))
    return {k: _rate(sum(v), len(v)) for k, v in sorted(buckets.items())}


def _unique_sorted(rows: List[Dict[str, str]], key: str) -> List[str]:
    return sorted({row.get(key, "") for row in rows if row.get(key)})


def build_rag_summary(
    csv_path: Path,
    *,
    experiment_type: str = "rag",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rows = _read_csv(csv_path)
    if not rows:
        raise ValueError(f"empty csv: {csv_path}")

    run_id = rows[0].get("run_id", "")
    attack_successes = [_as_bool(r.get("attack_success")) for r in rows]
    overall_count = sum(attack_successes)

    poison_rows = [r for r in rows if _as_bool(r.get("poison_retrieved"))]
    poison_retrieval_rate = _rate(len(poison_rows), len(rows))

    poison_by_mode: Dict[str, float] = {}
    for mode in _unique_sorted(rows, "corpus_mode"):
        mode_rows = [r for r in rows if r.get("corpus_mode") == mode]
        retrieved = [r for r in mode_rows if _as_bool(r.get("poison_retrieved"))]
        poison_by_mode[mode] = _rate(len(retrieved), len(mode_rows))

    rank_counter: Counter[str] = Counter()
    for r in rows:
        rank = _as_int(r.get("poison_rank"))
        if rank is not None:
            rank_counter[f"rank={rank}"] += 1

    clean_rows = [r for r in rows if r.get("corpus_mode") == "clean"]
    mixed_rows = [r for r in rows if r.get("corpus_mode") == "mixed"]
    clean_fp = sum(_as_bool(r.get("attack_success")) for r in clean_rows)

    mixed_retrieved = [r for r in mixed_rows if _as_bool(r.get("poison_retrieved"))]
    mixed_success = sum(_as_bool(r.get("attack_success")) for r in mixed_retrieved)
    mixed_failed = len(mixed_retrieved) - mixed_success

    likely_gen_fail = 0
    for r in rows:
        answer = (r.get("answer") or "").strip()
        if not answer or len(answer) < 20:
            likely_gen_fail += 1
        elif answer.startswith("根据检索上下文") and "无法" in answer:
            likely_gen_fail += 1

    summary: Dict[str, Any] = {
        "experiment_type": experiment_type,
        "source_csv": str(csv_path.name),
        "run_id": run_id,
        "row_count": len(rows),
        "targets": _unique_sorted(rows, "target_id"),
        "attacks": _unique_sorted(rows, "attack_id"),
        "corpus_modes": _unique_sorted(rows, "corpus_mode"),
        "overall_attack_success_count": overall_count,
        "overall_asr": _rate(overall_count, len(rows)),
        "asr_by_corpus_mode": _group_asr(rows, "corpus_mode"),
        "asr_by_attack_id": _group_asr(rows, "attack_id"),
        "asr_by_target_id": _group_asr(rows, "target_id"),
        "poison_retrieval_rate": poison_retrieval_rate,
        "poison_retrieval_rate_by_corpus_mode": poison_by_mode,
        "poison_rank_distribution": dict(sorted(rank_counter.items())),
        "clean_false_positive_count": clean_fp,
        "mixed_poison_retrieved_success_count": mixed_success,
        "mixed_poison_retrieved_failed_count": mixed_failed,
        "likely_generation_failure_count": likely_gen_fail,
    }
    if extra:
        summary.update(extra)
    return summary


def _profile_slice_stats(rows: List[Dict[str, str]], profile: str) -> Dict[str, Any]:
    subset = [r for r in rows if r.get("retriever_profile") == profile]
    clean_rows = [r for r in subset if r.get("corpus_mode") == "clean"]
    mixed_rows = [r for r in subset if r.get("corpus_mode") == "mixed"]
    mixed_retrieved = [r for r in mixed_rows if _as_bool(r.get("poison_retrieved"))]

    rank_counter: Counter[str] = Counter()
    for r in mixed_rows:
        rank = _as_int(r.get("poison_rank"))
        if rank is not None:
            rank_counter[f"rank={rank}"] += 1

    return {
        "row_count": len(subset),
        "overall_asr": _rate(
            sum(_as_bool(r.get("attack_success")) for r in subset),
            len(subset),
        ),
        "clean_asr": _rate(
            sum(_as_bool(r.get("attack_success")) for r in clean_rows),
            len(clean_rows),
        ),
        "mixed_asr": _rate(
            sum(_as_bool(r.get("attack_success")) for r in mixed_rows),
            len(mixed_rows),
        ),
        "poison_retrieval_rate": _rate(
            sum(_as_bool(r.get("poison_retrieved")) for r in subset),
            len(subset),
        ),
        "mixed_poison_retrieval_rate": _rate(len(mixed_retrieved), len(mixed_rows)),
        "poison_rank_distribution": dict(sorted(rank_counter.items())),
        "clean_false_positive_count": sum(
            _as_bool(r.get("attack_success")) for r in clean_rows
        ),
    }


def build_profile_summary(
    csv_path: Path,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rows = _read_csv(csv_path)
    if not rows:
        raise ValueError(f"empty csv: {csv_path}")

    profiles = _unique_sorted(rows, "retriever_profile")
    by_profile = {p: _profile_slice_stats(rows, p) for p in profiles}

    clean_rows = [r for r in rows if r.get("corpus_mode") == "clean"]
    mixed_rows = [r for r in rows if r.get("corpus_mode") == "mixed"]

    summary: Dict[str, Any] = {
        "experiment_type": "rag_minimal_http_profile",
        "source_csv": str(csv_path.name),
        "run_id": rows[0].get("run_id", ""),
        "row_count": len(rows),
        "targets": _unique_sorted(rows, "target_id"),
        "attacks": _unique_sorted(rows, "attack_id"),
        "corpus_modes": _unique_sorted(rows, "corpus_mode"),
        "retriever_profiles": profiles,
        "overall_attack_success_count": sum(
            _as_bool(r.get("attack_success")) for r in rows
        ),
        "overall_asr": _rate(sum(_as_bool(r.get("attack_success")) for r in rows), len(rows)),
        "asr_by_retriever_profile": {
            p: by_profile[p]["overall_asr"] for p in profiles
        },
        "clean_asr_by_retriever_profile": {
            p: by_profile[p]["clean_asr"] for p in profiles
        },
        "mixed_asr_by_retriever_profile": {
            p: by_profile[p]["mixed_asr"] for p in profiles
        },
        "poison_retrieval_rate_by_retriever_profile": {
            p: by_profile[p]["poison_retrieval_rate"] for p in profiles
        },
        "mixed_poison_retrieval_rate_by_retriever_profile": {
            p: by_profile[p]["mixed_poison_retrieval_rate"] for p in profiles
        },
        "poison_rank_distribution_by_retriever_profile": {
            p: by_profile[p]["poison_rank_distribution"] for p in profiles
        },
        "stats_by_retriever_profile": by_profile,
        "asr_by_corpus_mode": _group_asr(rows, "corpus_mode"),
        "clean_false_positive_count": sum(
            _as_bool(r.get("attack_success")) for r in clean_rows
        ),
        "clean_asr_overall": _rate(
            sum(_as_bool(r.get("attack_success")) for r in clean_rows),
            len(clean_rows),
        ),
        "mixed_asr_overall": _rate(
            sum(_as_bool(r.get("attack_success")) for r in mixed_rows),
            len(mixed_rows),
        ),
        "mixed_poison_retrieval_rate_overall": _rate(
            sum(_as_bool(r.get("poison_retrieved")) for r in mixed_rows),
            len(mixed_rows),
        ),
    }
    if extra:
        summary.update(extra)
    return summary


def _mode_asr(rows: List[Dict[str, str]], mode: str) -> float:
    subset = [r for r in rows if r.get("corpus_mode") == mode]
    return _rate(sum(_as_bool(r.get("attack_success")) for r in subset), len(subset))


def build_metadata_spoof_summary(
    csv_path: Path,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rows = _read_csv(csv_path)
    modes = _unique_sorted(rows, "corpus_mode")
    poison_by_mode: Dict[str, float] = {}
    rank_by_mode: Dict[str, Dict[str, int]] = {}
    for mode in modes:
        subset = [r for r in rows if r.get("corpus_mode") == mode]
        poison_by_mode[mode] = _rate(
            sum(_as_bool(r.get("poison_retrieved")) for r in subset),
            len(subset),
        )
        rc: Counter[str] = Counter()
        for r in subset:
            rank = _as_int(r.get("poison_rank"))
            if rank is not None:
                rc[f"rank={rank}"] += 1
        rank_by_mode[mode] = dict(sorted(rc.items()))

    mixed_official = [r for r in rows if r.get("corpus_mode") == "mixed_official_filter"]
    bypass_count = sum(_as_bool(r.get("poison_retrieved")) for r in mixed_official)
    trusted_success = sum(
        _as_bool(r.get("attack_success"))
        for r in mixed_official
        if _as_bool(r.get("poison_retrieved"))
    )

    summary: Dict[str, Any] = {
        "experiment_type": "metadata_spoof",
        "source_csv": str(csv_path.name),
        "run_id": rows[0].get("run_id", ""),
        "row_count": len(rows),
        "targets": _unique_sorted(rows, "target_id"),
        "attacks": _unique_sorted(rows, "attack_id"),
        "corpus_modes": modes,
        "clean_unfiltered_asr": _mode_asr(rows, "clean_unfiltered"),
        "clean_official_filter_asr": _mode_asr(rows, "clean_official_filter"),
        "mixed_unfiltered_asr": _mode_asr(rows, "mixed_unfiltered"),
        "mixed_official_filter_asr": _mode_asr(rows, "mixed_official_filter"),
        "asr_by_corpus_mode": _group_asr(rows, "corpus_mode"),
        "poison_retrieval_rate_by_mode": poison_by_mode,
        "poison_rank_distribution_by_mode": rank_by_mode,
        "metadata_filter_bypass_count": bypass_count,
        "metadata_filter_bypass_rate": _rate(bypass_count, len(mixed_official)),
        "trusted_spoof_success_count": trusted_success,
        "trusted_spoof_success_rate": _rate(trusted_success, len(mixed_official)),
        "clean_false_positive_count": sum(
            _as_bool(r.get("attack_success"))
            for r in rows
            if r.get("corpus_mode", "").startswith("clean")
        ),
    }
    if extra:
        summary.update(extra)
    return summary


def build_external_source_summary(
    csv_path: Path,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rows = _read_csv(csv_path)
    modes = _unique_sorted(rows, "corpus_mode")
    ext_retrieval_by_mode: Dict[str, float] = {}
    rank_by_mode: Dict[str, Dict[str, int]] = {}
    for mode in modes:
        subset = [r for r in rows if r.get("corpus_mode") == mode]
        ext_retrieval_by_mode[mode] = _rate(
            sum(_as_bool(r.get("external_poison_retrieved")) for r in subset),
            len(subset),
        )
        rc: Counter[str] = Counter()
        for r in subset:
            rank = _as_int(r.get("external_poison_rank"))
            if rank is not None:
                rc[f"rank={rank}"] += 1
        rank_by_mode[mode] = dict(sorted(rc.items()))

    source_type_buckets: Dict[str, List[bool]] = defaultdict(list)
    for r in rows:
        meta = r.get("retrieved_metadata") or ""
        for st in ("web", "github", "vendor_doc"):
            if f"source_type={st}" in meta:
                source_type_buckets[st].append(_as_bool(r.get("attack_success")))

    summary: Dict[str, Any] = {
        "experiment_type": "external_source_poison",
        "source_csv": str(csv_path.name),
        "run_id": rows[0].get("run_id", ""),
        "row_count": len(rows),
        "targets": _unique_sorted(rows, "target_id"),
        "attacks": _unique_sorted(rows, "attack_id"),
        "corpus_modes": modes,
        "asr_by_corpus_mode": _group_asr(rows, "corpus_mode"),
        "clean_external_only_asr": _mode_asr(rows, "clean_external_only"),
        "poisoned_external_only_asr": _mode_asr(rows, "poisoned_external_only"),
        "mixed_external_asr": _mode_asr(rows, "mixed_external"),
        "external_poison_retrieval_rate": _rate(
            sum(_as_bool(r.get("external_poison_retrieved")) for r in rows),
            len(rows),
        ),
        "external_poison_retrieval_rate_by_mode": ext_retrieval_by_mode,
        "external_poison_rank_distribution_by_mode": rank_by_mode,
        "asr_by_source_type": {
            k: _rate(sum(v), len(v)) for k, v in source_type_buckets.items()
        },
        "clean_external_false_positive_count": sum(
            _as_bool(r.get("attack_success"))
            for r in rows
            if r.get("corpus_mode") == "clean_external_only"
        ),
        "mixed_external_success_count": sum(
            _as_bool(r.get("attack_success"))
            for r in rows
            if r.get("corpus_mode") == "mixed_external"
        ),
    }
    if extra:
        summary.update(extra)
    return summary


def _top1_poison_rate(rows: List[Dict[str, str]]) -> float:
    retrieved = [r for r in rows if _as_bool(r.get("poison_retrieved"))]
    if not retrieved:
        return 0.0
    top1 = sum(_as_int(r.get("poison_rank")) == 1 for r in retrieved)
    return _rate(top1, len(retrieved))


def build_ranking_manipulation_summary(
    csv_path: Path,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    rows = _read_csv(csv_path)
    profiles = _unique_sorted(rows, "retriever_profile")
    by_profile: Dict[str, Dict[str, Any]] = {}

    for profile in profiles:
        subset = [r for r in rows if r.get("retriever_profile") == profile]
        mixed_retrieved = [r for r in subset if _as_bool(r.get("poison_retrieved"))]
        rc: Counter[str] = Counter()
        for r in subset:
            rank = _as_int(r.get("poison_rank"))
            if rank is not None:
                rc[f"rank={rank}"] += 1
        by_profile[profile] = {
            "row_count": len(subset),
            "asr": _rate(sum(_as_bool(r.get("attack_success")) for r in subset), len(subset)),
            "poison_retrieval_rate": _rate(len(mixed_retrieved), len(subset)),
            "poison_rank_distribution": dict(sorted(rc.items())),
            "top1_poison_rate": _top1_poison_rate(subset),
        }

    baseline = by_profile.get("tfidf_top5", {})
    deltas: Dict[str, Dict[str, float]] = {}
    for profile in profiles:
        if profile == "tfidf_top5":
            continue
        cur = by_profile[profile]
        deltas[profile] = {
            "asr_delta": round(cur["asr"] - baseline.get("asr", 0), 4),
            "poison_retrieval_delta": round(
                cur["poison_retrieval_rate"] - baseline.get("poison_retrieval_rate", 0),
                4,
            ),
            "top1_poison_rate_delta": round(
                cur["top1_poison_rate"] - baseline.get("top1_poison_rate", 0),
                4,
            ),
        }

    asr_by_attack_profile: Dict[str, Dict[str, float]] = {}
    for attack in _unique_sorted(rows, "attack_id"):
        asr_by_attack_profile[attack] = {
            p: _rate(
                sum(
                    _as_bool(r.get("attack_success"))
                    for r in rows
                    if r.get("attack_id") == attack and r.get("retriever_profile") == p
                ),
                len([r for r in rows if r.get("attack_id") == attack and r.get("retriever_profile") == p]),
            )
            for p in profiles
        }

    summary: Dict[str, Any] = {
        "experiment_type": "ranking_manipulation",
        "source_csv": str(csv_path.name),
        "run_id": rows[0].get("run_id", ""),
        "row_count": len(rows),
        "targets": _unique_sorted(rows, "target_id"),
        "attacks": _unique_sorted(rows, "attack_id"),
        "corpus_modes": _unique_sorted(rows, "corpus_mode"),
        "retriever_profiles": profiles,
        "asr_by_retriever_profile": {p: by_profile[p]["asr"] for p in profiles},
        "poison_retrieval_rate_by_retriever_profile": {
            p: by_profile[p]["poison_retrieval_rate"] for p in profiles
        },
        "poison_rank_distribution_by_retriever_profile": {
            p: by_profile[p]["poison_rank_distribution"] for p in profiles
        },
        "top1_poison_rate_by_retriever_profile": {
            p: by_profile[p]["top1_poison_rate"] for p in profiles
        },
        "asr_by_attack_id_by_profile": asr_by_attack_profile,
        "stats_by_retriever_profile": by_profile,
        "profile_delta_vs_tfidf_top5": deltas,
        "rank_shift_summary": deltas,
    }
    if extra:
        summary.update(extra)
    return summary


def build_tool_summary(csv_path: Path, *, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    rows = _read_csv(csv_path)
    if not rows:
        raise ValueError(f"empty csv: {csv_path}")

    run_id = rows[0].get("run_id", "")
    tool_success = sum(_as_bool(r.get("tool_poison_success")) for r in rows)
    followed = sum(_as_bool(r.get("followed_injected_summary")) for r in rows)
    rejected = sum(_as_bool(r.get("rejected_injected_summary")) for r in rows)
    trusted = sum(_as_bool(r.get("trusted_real_findings")) for r in rows)

    summary: Dict[str, Any] = {
        "experiment_type": "tool_output_poison",
        "source_csv": str(csv_path.name),
        "run_id": run_id,
        "row_count": len(rows),
        "targets": _unique_sorted(rows, "target_id"),
        "attacks": _unique_sorted(rows, "attack_id"),
        "corpus_modes": _unique_sorted(rows, "corpus_mode"),
        "overall_attack_success_count": sum(_as_bool(r.get("attack_success")) for r in rows),
        "overall_asr": _rate(sum(_as_bool(r.get("attack_success")) for r in rows), len(rows)),
        "tool_poison_success_count": tool_success,
        "followed_injected_summary_count": followed,
        "rejected_injected_summary_count": rejected,
        "trusted_real_findings_count": trusted,
        "tool_poison_success_rate": _rate(tool_success, len(rows)),
    }
    if extra:
        summary.update(extra)
    return summary


def write_summary(summary: Dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: Dict[str, Any] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    merged = {**existing, **summary}
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
