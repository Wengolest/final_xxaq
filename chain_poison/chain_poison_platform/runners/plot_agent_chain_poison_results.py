"""
Agent Chain Poison 实验结果可视化（面向数学建模展示）。

推荐用于建模的数据：
1. 攻击效能矩阵 M (5×6)：poison_type × 各偏移指标发生率，可用于加权评分、聚类。
2. 攻击链闭环率 η = strict_success / reasoning_shift：衡量“推理偏移→攻击成功”传导效率。
3. 风险传导系数 κ = decision_shift / reasoning_shift：衡量推理偏移向决策层传播比例。
4. 单样本 0/1 指标列：可进一步做 Logistic 回归、ROC、混淆矩阵。

用法:
  python -m runners.plot_agent_chain_poison_results
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PLATFORM_ROOT = Path(__file__).resolve().parent.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

DEFAULT_CSV = PLATFORM_ROOT / "outputs" / "agent_chain_poison" / "agent_chain_poison_merged_results.csv"
DEFAULT_FIG = PLATFORM_ROOT / "outputs" / "agent_chain_poison" / "agent_chain_poison_modeling_figure.png"

POISON_ORDER = [
    "logical_rule_injection",
    "priority_shift_injection",
    "step_order_hijack",
    "evidence_suppression",
    "autonomous_action_drift",
]

POISON_LABELS = {
    "logical_rule_injection": "伪逻辑规则注入",
    "priority_shift_injection": "优先级偏移注入",
    "step_order_hijack": "步骤顺序劫持",
    "evidence_suppression": "证据抑制",
    "autonomous_action_drift": "自治执行偏移",
}

METRIC_COLS = [
    "reasoning_shift",
    "decision_shift",
    "risk_downgrade",
    "autonomous_action",
    "strict_success",
]

METRIC_LABELS = [
    "推理偏移率",
    "决策偏移率",
    "风险降级率",
    "自治执行率",
    "攻击成功率",
]


def load_effectiveness_matrix(csv_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    for col in METRIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    rate_rows = []
    for pt in POISON_ORDER:
        sub = df[df["poison_type"] == pt]
        row = {"poison_type": pt}
        for col in METRIC_COLS:
            row[col] = sub[col].mean() if len(sub) else 0.0
        rate_rows.append(row)
    rates = pd.DataFrame(rate_rows).set_index("poison_type")

    # 建模派生指标
    derived = pd.DataFrame(index=POISON_ORDER)
    derived["攻击链闭环率 η"] = np.where(
        rates["reasoning_shift"] > 0,
        rates["strict_success"] / rates["reasoning_shift"],
        0.0,
    )
    derived["风险传导系数 κ"] = np.where(
        rates["reasoning_shift"] > 0,
        rates["decision_shift"] / rates["reasoning_shift"],
        0.0,
    )
    derived["决策-成功比"] = np.where(
        rates["decision_shift"] > 0,
        rates["strict_success"] / rates["decision_shift"],
        0.0,
    )
    return rates, derived


def plot_modeling_figure(
    rates: pd.DataFrame,
    derived: pd.DataFrame,
    *,
    output_path: Path,
    total_strict: float,
) -> Path:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    matrix = rates.loc[POISON_ORDER, METRIC_COLS].values
    ylabels = [POISON_LABELS[p] for p in POISON_ORDER]

    fig = plt.figure(figsize=(14, 7.5), dpi=150)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.28)

    # 左：攻击效能矩阵热力图（建模主矩阵 M）
    ax1 = fig.add_subplot(gs[0, 0])
    sns.heatmap(
        matrix,
        annot=True,
        fmt=".0%",
        cmap="YlOrRd",
        vmin=0,
        vmax=1,
        xticklabels=METRIC_LABELS,
        yticklabels=ylabels,
        linewidths=0.6,
        linecolor="white",
        cbar_kws={"label": "发生率"},
        ax=ax1,
    )
    ax1.set_title("攻击效能矩阵 M (5×5)\npoison_type × 偏移指标发生率", fontsize=13, pad=12)
    ax1.set_xlabel("")
    ax1.set_ylabel("攻击类型")

    # 右：攻击链闭环率 η 与 strict_success 对比
    ax2 = fig.add_subplot(gs[0, 1])
    x = np.arange(len(POISON_ORDER))
    width = 0.36
    eta = derived.loc[POISON_ORDER, "攻击链闭环率 η"].values
    strict = rates.loc[POISON_ORDER, "strict_success"].values

    bars1 = ax2.bar(x - width / 2, strict, width, label="攻击成功率 (strict_success)", color="#d62728")
    bars2 = ax2.bar(x + width / 2, eta, width, label="攻击链闭环率 η = success/reasoning", color="#1f77b4")
    ax2.set_xticks(x)
    ax2.set_xticklabels([POISON_LABELS[p] for p in POISON_ORDER], rotation=18, ha="right")
    ax2.set_ylim(0, 1.08)
    ax2.set_ylabel("比率")
    ax2.set_title("攻击链传导效率对比\nη 衡量推理偏移能否闭环为攻击成功", fontsize=13, pad=12)
    ax2.legend(loc="upper right", fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.35)

    for bar in bars1:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.02, f"{h:.0%}", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.02, f"{h:.0%}", ha="center", va="bottom", fontsize=8)

    fig.suptitle(
        f"普适 Agent 多步推理链投毒评测（N=100，fast模式） | 总攻击成功率 = {total_strict:.1%}",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_path


def main() -> None:
    csv_path = DEFAULT_CSV
    if not csv_path.is_file():
        raise FileNotFoundError(f"Merged CSV not found: {csv_path}")

    rates, derived = load_effectiveness_matrix(csv_path)
    total_strict = rates["strict_success"].mean()

    out = plot_modeling_figure(rates, derived, output_path=DEFAULT_FIG, total_strict=total_strict)

    print("=== 推荐用于数学建模的数据 ===")
    print("\n1. 攻击效能矩阵 M (poison_type × 指标发生率):")
    print((rates.loc[POISON_ORDER, METRIC_COLS] * 100).round(1).astype(str) + "%")
    print("\n2. 派生建模指标 (η, κ):")
    print((derived.loc[POISON_ORDER] * 100).round(1).astype(str) + "%")
    print(f"\n3. 总攻击成功率: {total_strict:.2%}")
    print(f"\nFigure saved -> {out}")


if __name__ == "__main__":
    main()
