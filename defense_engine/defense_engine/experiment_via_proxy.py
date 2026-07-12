# ============================================================
# 通用实验脚本 — 通过 HTTP 代理测试 42 条样本
#
# 零 Agent 框架依赖。向 defense_proxy (:8200) 发送
# OpenAI 格式的 HTTP 请求，收集防御引擎的拦截数据，
# 输出 DSR / FPR / 各层拦截率报告。
#
# 用法:
#   1. 先启动代理: uvicorn defense_proxy:app --host 0.0.0.0 --port 8200
#   2. python experiment_via_proxy.py
#   3. (可选) set DEFENSE_PROXY_URL=http://localhost:8200 覆盖地址
# ============================================================

import sys, os, io, json, time

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ---- 依赖检查 (无需 Agent 框架) ----
try:
    import httpx
except ImportError:
    print("需要 httpx: pip install httpx")
    sys.exit(1)

# ---- 配置 ----
PROXY_URL = os.getenv("DEFENSE_PROXY_URL", "http://localhost:8200")
CHAT_URL = f"{PROXY_URL}/v1/chat/completions"
HEALTH_URL = f"{PROXY_URL}/health"
TIMEOUT = 60

from samples import SAMPLES


# ============================================================
# 一、42 条测试样本 (与 experiment.py 一致)
# ============================================================

# ---- 样本定义: 统一导入自 samples.py (65条) ----
# (已从顶部 from samples import SAMPLES 导入)




# ============================================================
# 二、代理健康检查
# ============================================================

def check_health() -> dict:
    """检查代理是否在运行"""
    try:
        r = httpx.get(HEALTH_URL, timeout=5)
        return r.json()
    except Exception as e:
        print(f"Cannot connect to proxy at {PROXY_URL}: {e}")
        print("Make sure: uvicorn defense_proxy:app --host 0.0.0.0 --port 8200")
        sys.exit(1)


# ============================================================
# 三、运行单条样本
# ============================================================

def run_sample(sample: dict) -> dict:
    """发送一条样本到防御代理，返回判决结构"""
    body = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": sample["content"]}],
        "max_tokens": 500,
        "stream": False,
    }

    result = {
        "id": sample["id"],
        "family": sample["family"],
        "is_attack": sample["is_attack"],
        "content": sample["content"][:80],
        "verdict": "unknown",         # blocked / passed / llm_refused / error
        "blocked_by": "",              # 防御引擎哪层拦的
        "risk_score": 0.0,
        "layer_details": {},           # 逐层详情
        "error_message": "",
        "elapsed_ms": 0,
    }

    t0 = time.perf_counter()
    try:
        r = httpx.post(CHAT_URL, json=body, timeout=TIMEOUT)
    except httpx.TimeoutException:
        result["verdict"] = "error"
        result["error_message"] = "Timeout"
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        return result
    except Exception as e:
        result["verdict"] = "error"
        result["error_message"] = str(e)[:100]
        result["elapsed_ms"] = (time.perf_counter() - t0) * 1000
        return result

    result["elapsed_ms"] = (time.perf_counter() - t0) * 1000

    try:
        data = r.json()
    except Exception:
        result["verdict"] = "error"
        result["error_message"] = f"HTTP {r.status_code}: {r.text[:100]}"
        return result

    # ---- 判断判决 ----

    # 有 error → 被防御拦截
    if "error" in data:
        error_info = data["error"]
        result["verdict"] = "blocked"
        result["risk_score"] = data.get("defense_risk_score", 0.0)
        result["error_message"] = error_info.get("message", "")[:120]

        # 提取被哪层拦的 (从 error message 或 layer_details 中分析)
        layer_details = data.get("defense_layer_details", [])
        if layer_details:
            result["layer_details"] = layer_details
            result["blocked_by"] = _find_blocking_layer_from_details(layer_details)
        return result

    # 有 choices → 放行, 检查防御元数据
    defense = data.get("defense", {})
    result["risk_score"] = defense.get("risk_score", 0.0)
    input_layers = defense.get("input_layers", [])
    output_layers = defense.get("output_layers", [])

    # 判断是否有层 warn/block (即使最终放行)
    any_warn = False
    for item in input_layers + output_layers:
        for lr in item.get("layers", []):
            if lr.get("action") in ("warn", "block"):
                any_warn = True
    if any_warn:
        result["verdict"] = "warned"
    else:
        result["verdict"] = "passed"

    result["layer_details"] = {
        "input_layers": input_layers,
        "output_layers": output_layers,
    }

    return result


def _find_blocking_layer_from_details(details: list) -> str:
    """从 layer_details 中找出是哪个层拦的"""
    for item in details:
        for lr in item.get("layers", []):
            if not lr.get("passed", True) or lr.get("action") in ("block", "quarantine"):
                return lr["layer"]
    return "unknown"


# ============================================================
# 四、指标计算
# ============================================================

def compute_metrics(results: list[dict]) -> dict:
    """从所有样本结果计算 DSR / FPR / 各层拦截率"""
    total = len(results)
    attacks = [r for r in results if r["is_attack"]]
    benigns = [r for r in results if not r["is_attack"]]

    # DSR = 攻击样本中被拦截(warn也算命中)的比例
    attack_total = len(attacks)
    attack_blocked = sum(1 for r in attacks if r["verdict"] in ("blocked", "warned"))
    dsr = attack_blocked / attack_total if attack_total > 0 else 0.0

    # FPR = 正常样本中被错误拦截的比例
    benign_total = len(benigns)
    benign_blocked = sum(1 for r in benigns if r["verdict"] in ("blocked",))
    fpr = benign_blocked / benign_total if benign_total > 0 else 0.0

    # 严格命中率 (只算真正 blocked 的)
    attack_strict_blocked = sum(1 for r in attacks if r["verdict"] == "blocked")
    dsr_strict = attack_strict_blocked / attack_total if attack_total > 0 else 0.0

    # 各层拦截率
    layer_names = ["source_governance", "model_interaction", "memory_control",
                   "tool_constraint", "decision_supervision"]
    layer_blocked = {n: 0 for n in layer_names}

    for r in results:
        if r["verdict"] in ("blocked", "warned"):
            blocked_by = r.get("blocked_by", "")
            if blocked_by in layer_blocked:
                layer_blocked[blocked_by] += 1

    # 各攻击族 DSR
    family_dsr = {}
    for r in attacks:
        f = r["family"]
        if f not in family_dsr:
            family_dsr[f] = {"total": 0, "blocked": 0}
        family_dsr[f]["total"] += 1
        if r["verdict"] in ("blocked", "warned"):
            family_dsr[f]["blocked"] += 1

    # 延迟统计
    latencies = [r["elapsed_ms"] for r in results]

    return {
        "total_samples": total,
        "attack_samples": attack_total,
        "benign_samples": benign_total,
        "dsr": dsr,
        "dsr_strict": dsr_strict,
        "fpr": fpr,
        "attack_blocked": attack_blocked,
        "benign_blocked": benign_blocked,
        "layer_blocked": layer_blocked,
        "family_dsr": family_dsr,
        "latency_p50": sorted(latencies)[len(latencies)//2] if latencies else 0,
        "latency_p99": sorted(latencies)[int(len(latencies)*0.99)] if latencies else 0,
    }


# ============================================================
# 五、报告输出
# ============================================================

SEP = "=" * 80
SUB = "-" * 80


def print_report(results: list[dict], metrics: dict, mode: str):
    """打印完整实验报告"""
    print(f"\n{SEP}")
    print(f"  EXPERIMENT REPORT — via Proxy ({mode})")
    print(f"  Proxy: {PROXY_URL} | {metrics['total_samples']} samples")
    print(SEP)

    # 总体指标
    print(f"\n  DSR (Detection Rate):     {metrics['dsr']:.1%}  ({metrics['attack_blocked']}/{metrics['attack_samples']} attacks)")
    print(f"  DSR (strict, blocked only): {metrics['dsr_strict']:.1%}")
    print(f"  FPR (False Positive Rate):  {metrics['fpr']:.1%}  ({metrics['benign_blocked']}/{metrics['benign_samples']} benign)")
    print(f"  Latency: P50={metrics['latency_p50']:.0f}ms  P99={metrics['latency_p99']:.0f}ms")

    # 各层拦截贡献
    print(f"\n  Layer Block Distribution:")
    for layer, count in sorted(metrics["layer_blocked"].items(), key=lambda x: -x[1]):
        bar = "#" * count
        print(f"    {layer:<28s} {count:>2d}  {bar}")

    # 各攻击族 DSR
    print(f"\n  Attack Family DSR:")
    for family, stats in sorted(metrics["family_dsr"].items(), key=lambda x: -(x[1]["blocked"]/max(x[1]["total"],1))):
        rate = stats["blocked"] / max(stats["total"], 1)
        print(f"    {family:<26s} {rate:.0%}  ({stats['blocked']}/{stats['total']})")

    # 逐样本详情
    print(f"\n  Per-Sample Detail:")
    print(f"  {'ID':<6s} {'Verdict':<10s} {'is_attack':<10s} {'Risk':<6s} {'Family':<22s} {'Blocked By':<22s}")
    print(f"  {SUB}")
    for r in results:
        verdict = r["verdict"].upper()
        icon = {"BLOCKED": " BLOCK", "WARNED": " WARN ", "PASSED": " PASS "}.get(verdict, f" {verdict[:6]} ")
        print(f"  {r['id']:<6s} {icon:<10s} {str(r['is_attack']):<10s} "
              f"{r['risk_score']:<6.2f} {r['family']:<22s} {r.get('blocked_by','-'):<22s}")

    # 混淆矩阵
    tp = metrics["attack_blocked"]
    fn = metrics["attack_samples"] - tp
    fp = metrics["benign_blocked"]
    tn = metrics["benign_samples"] - fp

    print(f"\n  Confusion Matrix:")
    print(f"                     Predicted Attack   Predicted Benign")
    print(f"    Actual Attack         TP={tp:<4d}          FN={fn}")
    print(f"    Actual Benign         FP={fp:<4d}          TN={tn}")
    print(f"\n    Accuracy: {(tp+tn)/max(metrics['total_samples'],1):.1%}")

    print(f"\n{SEP}\n")


def print_layer_trace(results: list[dict]):
    """打印每条样本的逐层详情"""
    print(f"\n{'='*80}")
    print(f"  PER-SAMPLE LAYER TRACE")
    print(f"{'='*80}")

    layer_order = ["source_governance", "model_interaction", "memory_control",
                   "tool_constraint", "decision_supervision"]

    for r in results:
        if r["verdict"] == "passed" and not r["risk_score"]:
            continue  # 跳过完全干净的

        print(f"\n  [{r['verdict'].upper()}] {r['id']} | {r['family']} | risk={r['risk_score']:.2f}")
        print(f"  Content: {r['content'][:70]}")
        print(f"  {SUB}")

        details = r.get("layer_details", {})
        # layer_details 可能有两种格式:
        #   - list: 来自 defense_proxy 的 defense_layer_details (请求被拦截时)
        #   - dict: 来自 defense_proxy 的 defense.input_layers/output_layers (请求放行时)
        if isinstance(details, list):
            all_layers = details
        elif isinstance(details, dict):
            all_layers = details.get("input_layers", []) + details.get("output_layers", [])
        else:
            all_layers = []

        for item in all_layers:
            if isinstance(item, dict):
                layers = item.get("layers", [])
                for lr in layers:
                    if lr.get("action") not in ("pass",) or lr.get("flags"):
                        print(f"    {lr['layer']:<28s} {lr['action']:<6s} "
                              f"risk={lr.get('risk_score',0):.2f} rules={lr.get('matched_rules',[])} "
                              f"flags={lr.get('flags',[])[:2]}")


# ============================================================
# 六、主入口
# ============================================================

if __name__ == "__main__":
    # 1. 健康检查
    health = check_health()
    mode = health.get("mode", "balanced")
    print(f"Proxy OK — {health['backend']} | mode={mode} | {health['rules_loaded']} rules")

    # 2. 跑全部样本
    print(f"\nRunning {len(SAMPLES)} samples...")
    results = []
    for i, sample in enumerate(SAMPLES):
        r = run_sample(sample)
        results.append(r)

        # 逐条即时显示
        icon = {"blocked": "BLOCK", "warned": "WARN", "passed": "PASS"}.get(r["verdict"], "????")
        print(f"  [{icon}] {r['id']:<6s} | {r['family']:<22s} | "
              f"risk={r['risk_score']:.2f} | {r['elapsed_ms']:.0f}ms | {r.get('blocked_by','-')}")

    # 3. 计算指标
    metrics = compute_metrics(results)

    # 4. 打印报告
    print_report(results, metrics, mode)

    # 5. 打印有告警的样本逐层 trace
    print_layer_trace(results)

    # 6. 保存结果
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "experiment_via_proxy_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "proxy_url": PROXY_URL,
            "mode": mode,
            "samples": len(SAMPLES),
            "metrics": {k: v for k, v in metrics.items() if k != "family_dsr"},
            "family_dsr": {k: {"total": v["total"], "blocked": v["blocked"],
                               "rate": v["blocked"]/max(v["total"],1)}
                           for k, v in metrics["family_dsr"].items()},
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"Results saved to: {output_file}")
