# ============================================================
# 标准化实验脚本
# 用法: python experiment.py
# 输出: 完整指标报告 (DSR/FPR/FNR/混淆矩阵/各层拦截率/攻击族DSR/延迟)
# ============================================================

import sys, os, io, json, time

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from orchestrator import DefenseOrchestrator
from defense_types import DefenseContext, DefenseMode
from rule_engine import RuleEngine
from agent_adapter import DefenseWrapper
from mock_agent import MockAgent
from metrics import DefenseMetrics
from samples import SAMPLES


# ============================================================
# 一、加载规则引擎 (42 条内置规则)
# ============================================================

with open(os.path.join(ROOT, "config", "defense_rules.json"), encoding="utf-8") as f:
    rules = [r for r in json.load(f)["rules"] if "rule_id" in r]
engine = RuleEngine(rules)


# ============================================================
# 二、定义测试样本集
# 字段: id / content / source / is_attack / family / role
# ============================================================

# ---- 样本定义: 统一导入自 samples.py (65条: 20良性 + 45攻击) ----
# (已从顶部 from samples import SAMPLES 导入)




# ============================================================
# 三、运行实验 — 三种模式 × 全样本
# ============================================================

SEP = "=" * 80

def run_experiment(label: str, mode: DefenseMode):
    print(f"\n{SEP}")
    print(f"  实验模式: {label} ({mode.value})")
    print(SEP)

    orch = DefenseOrchestrator(engine, mode=mode)
    metrics = DefenseMetrics()
    t_start = time.perf_counter()

    for i, s in enumerate(SAMPLES):
        # 每条样本构造独立的 Agent + Wrapper
        agent = MockAgent(role=s["role"])
        wrapper = DefenseWrapper(agent, orch, mode=mode)

        # 根据角色选择方法
        if s["role"] == "devops":
            result = wrapper.run_with_tools(s["content"], s["source"])
        else:
            result = wrapper.run_with_defense(s["content"], s["source"])

        # 判定 verdict
        if not result.success:
            verdict = "blocked"
        elif result.action == "warn":
            verdict = "warned"
        else:
            verdict = "passed"

        # 记录到指标引擎
        metrics.record_verdict(
            verdict=verdict,
            risk_score=result.risk_score,
            is_attack=s["is_attack"],
            attack_family=s["family"],
            blocking_layer=result.blocked_by if not result.success else None,
        )

        # 逐条打印 (简洁)
        status_icon = (
            "BLOCK" if not result.success else
            "WARN" if result.action == "warn" else
            "PASS"
        )
        expected = "attack" if s["is_attack"] else "benign"
        print(f"  [{status_icon}] {s['id']:5s} | {expected:6s} | {s['family']:22s} | "
              f"risk={result.risk_score:.2f} | blocked_by={result.blocked_by or '-'}")

    elapsed = (time.perf_counter() - t_start) * 1000
    print(f"\n  总样本: {len(SAMPLES)}  耗时: {elapsed:.0f}ms")
    print(SEP)
    metrics.print_report()
    print()

    return metrics


# ============================================================
# 四、主入口 — 三种模式顺序执行
# ============================================================

if __name__ == "__main__":
    print("=" * 80)
    print("  LLM Agent Defense Engine — 标准化实验")
    print(f"  规则: {engine.rule_count} 条加载 / {engine.enabled_rule_count} 条启用")
    print(f"  样本: {len(SAMPLES)} 条 (攻击={sum(1 for s in SAMPLES if s['is_attack'])}"
          f" / 正常={sum(1 for s in SAMPLES if not s['is_attack'])})")
    print(f"  模式: STRICT / BALANCED / PERMISSIVE")
    print(f"  攻击族: {len(set(s['family'] for s in SAMPLES))} 类")
    print("=" * 80)

    run_experiment("STRICT (严格)",     DefenseMode.STRICT)
    run_experiment("BALANCED (均衡)",   DefenseMode.BALANCED)
    run_experiment("PERMISSIVE (宽松)", DefenseMode.PERMISSIVE)

    print("=" * 80)
    print("  实验完成")
    print("=" * 80)
