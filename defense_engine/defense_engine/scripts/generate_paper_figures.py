"""
Generate paper figures for §3 (Exp2-Exp5) using matplotlib.

Output: paper_figures/
  exp2_overview.png   — 5 Agent DSR bar + stacked verdict distribution
  exp2_heatmap.png    — 9 attack families × 5 Agents heatmap
  exp3.png            — Tool abuse: with vs without defense comparison
  exp4.png            — RAG poison: 3-config comparison
  exp5.png            — Ablation: 5-config DSR comparison
"""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path
from collections import Counter

# ── Config ──────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

OUTPUT_DIR = Path(__file__).parent.parent / "paper_figures"
OUTPUT_DIR.mkdir(exist_ok=True)

DATA_PATH = Path(__file__).parent.parent / "data" / "experiments.json"

# ── Color palette ───────────────────────────────────────────
C_BLOCKED = "#f5222d"
C_REFUSED = "#fa8c16"
C_COMPROMISED = "#722ed1"
C_WARNED = "#faad14"
C_PASSED = "#52c41a"
C_BENIGN = "#1677ff"
C_DEFENSE = "#1890ff"
C_NO_DEFENSE = "#bfbfbf"
AGENT_COLORS = ["#1677ff", "#52c41a", "#722ed1", "#fa8c16", "#f5222d"]
AGENT_LABELS = ["A (Chat)", "B (Tool)", "C (RAG)", "D (Langroid)", "E (Smol)"]
AGENT_KEYS = [
    "MANUAL_20260607_124351",  # A
    "MANUAL_20260607_124923",  # B
    "MANUAL_20260607_125446",  # C
    "MANUAL_20260607_130027",  # D
    "MANUAL_20260607_132455",  # E
]

FAMILY_ORDER = [
    "prompt_injection", "jailbreak", "encoding_obfuscation",
    "zero_width", "context_escalation", "pii_leakage",
    "memory_poisoning", "tool_misuse", "multi_turn_composite",
]
FAMILY_LABELS = [
    "提示注入", "越狱", "编码混淆",
    "零宽字符", "上下文越权", "PII泄露",
    "记忆投毒", "工具滥用", "多轮复合",
]

# ── Helpers ─────────────────────────────────────────────────
def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def fmt_pct(v):
    return f"{v * 100:.1f}%"


# ═══════════════════════════════════════════════════════════
# Exp2: 5-Agent comparison
# ═══════════════════════════════════════════════════════════

def fig_exp2_overview(data):
    """DSR bar chart + stacked Blocked/Refused/Compromised distribution."""
    agents_metrics = [data[k]["metrics"] for k in AGENT_KEYS]

    dsr_vals = [m["dsr"] for m in agents_metrics]
    blocked_vals = [m.get("attack_blocked", 0) for m in agents_metrics]
    refused_vals = [m.get("attack_refused", 0) for m in agents_metrics]
    compromised_vals = [m.get("attack_compromised", 0) for m in agents_metrics]
    fpr_vals = [m.get("fpr", 0) for m in agents_metrics]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1, 1.2]})

    # Left: DSR bar chart
    x = np.arange(len(AGENT_LABELS))
    bars = ax1.bar(x, dsr_vals, color=AGENT_COLORS, edgecolor="white", linewidth=0.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(AGENT_LABELS, fontsize=9)
    ax1.set_ylim(0, 1.1)
    ax1.set_ylabel("DSR", fontsize=11)
    ax1.set_title("5 Agent DSR 对比", fontsize=13, fontweight="bold")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax1.grid(axis="y", alpha=0.3)
    for bar, val in zip(bars, dsr_vals):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                 f"{val:.1%}", ha="center", fontsize=10, fontweight="bold")

    # Right: Stacked bar (Blocked/Refused/Compromised)
    ax2.bar(x, blocked_vals, color=C_BLOCKED, label="Blocked (代理拦截)", edgecolor="white")
    ax2.bar(x, refused_vals, bottom=blocked_vals, color=C_REFUSED, label="Refused (LLM拒绝)", edgecolor="white")
    bottom2 = [b + r for b, r in zip(blocked_vals, refused_vals)]
    ax2.bar(x, compromised_vals, bottom=bottom2, color=C_COMPROMISED, label="Compromised (被攻破)", edgecolor="white")
    ax2.set_xticks(x)
    ax2.set_xticklabels(AGENT_LABELS, fontsize=9)
    ax2.set_ylabel("样本数", fontsize=11)
    ax2.set_title("Verdict 堆叠分布 (45 条攻击样本)", fontsize=13, fontweight="bold")
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(axis="y", alpha=0.3)
    # Annotate totals
    for i in range(len(x)):
        total = blocked_vals[i] + refused_vals[i] + compromised_vals[i]
        ax2.text(i, total + 0.5, str(total), ha="center", fontsize=9)

    fig.suptitle("实验二：多 Agent 代理防护总体结果", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "exp2_overview.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> exp2_overview.png (DSR={dsr_vals}, compromised={compromised_vals})")


def fig_exp2_heatmap(data):
    """9 families × 5 Agents DSR heatmap."""
    matrix = np.zeros((len(FAMILY_ORDER), len(AGENT_KEYS)))
    for j, key in enumerate(AGENT_KEYS):
        fd = data[key]["metrics"].get("family_dsr", {})
        for i, fam in enumerate(FAMILY_ORDER):
            if fam in fd:
                f = fd[fam]
                total = max(f["total"], 1)
                matrix[i, j] = (f["blocked"] + f["refused"]) / total

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(matrix, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")

    ax.set_xticks(np.arange(len(AGENT_LABELS)))
    ax.set_xticklabels(AGENT_LABELS, fontsize=10)
    ax.set_yticks(np.arange(len(FAMILY_LABELS)))
    ax.set_yticklabels(FAMILY_LABELS, fontsize=9)

    # Annotate cells
    for i in range(len(FAMILY_ORDER)):
        for j in range(len(AGENT_KEYS)):
            val = matrix[i, j]
            color = "white" if val < 0.5 else "black"
            ax.text(j, i, f"{val:.1%}", ha="center", va="center", fontsize=9, color=color)

    ax.set_title("攻击族 × Agent DSR 热力图", fontsize=13, fontweight="bold")
    fig.colorbar(im, ax=ax, label="DSR", shrink=0.85)
    fig.suptitle("实验二：9 族攻击在 5 个 Agent 下的拦截率矩阵", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "exp2_heatmap.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> exp2_heatmap.png")


# ═══════════════════════════════════════════════════════════
# Exp3: Tool abuse — with vs without defense
# ═══════════════════════════════════════════════════════════

def fig_exp3(data):
    """Per-sample verdict heatmap + tool execution comparison."""
    k_def = "MANUAL_20260607_145147"
    k_none = "MANUAL_20260607_145148"

    res_def = data[k_def]["results"]
    res_none = data[k_none]["results"]
    m_def = data[k_def]["metrics"]
    m_none = data[k_none]["metrics"]

    sample_ids = ["TM01", "TM02", "TM03", "N01", "N02", "N03"]
    sample_labels = ["TM01\nrm -rf /", "TM02\ncurl|bash", "TM03\n读/etc/passwd", "N01\nkubectl", "N02\nls /tmp", "N03\ndf -h"]

    # Build per-sample verdict matrix
    verdict_to_val = {"blocked": 0, "refused": 1, "compromised": 2, "passed": 3, "warned": 4}
    val_to_color = {0: C_BLOCKED, 1: C_REFUSED, 2: C_COMPROMISED, 3: C_PASSED, 4: C_WARNED}
    val_to_label = {0: "Blocked", 1: "Refused", 2: "Compromised", 3: "Passed", 4: "Warned"}

    def get_verdict_val(results, sid):
        for r in results:
            if r["id"] == sid:
                return verdict_to_val.get(r.get("verdict", "passed"), 3)
        return 3

    matrix = np.zeros((len(sample_ids), 2))
    for i, sid in enumerate(sample_ids):
        matrix[i, 0] = get_verdict_val(res_def, sid)
        matrix[i, 1] = get_verdict_val(res_none, sid)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.2, 1]})

    # Left: Per-sample verdict heatmap
    cmap = matplotlib.colors.ListedColormap([C_BLOCKED, C_REFUSED, C_COMPROMISED, C_PASSED, C_WARNED])
    im = ax1.imshow(matrix.T, cmap=cmap, aspect="auto", vmin=0, vmax=4)
    ax1.set_xticks(np.arange(len(sample_ids)))
    ax1.set_xticklabels(sample_labels, fontsize=7, rotation=30, ha="right")
    ax1.set_yticks([0, 1])
    ax1.set_yticklabels(["有防御\n(via proxy)", "无防御\n(直连)"], fontsize=9)
    ax1.set_title("逐样本 Verdict 对比", fontsize=12, fontweight="bold")
    for i in range(len(sample_ids)):
        for j in range(2):
            v = int(matrix[i, j])
            ax1.text(i, j, val_to_label[v], ha="center", va="center", fontsize=7,
                    color="white" if v in (0, 2) else "black", fontweight="bold")

    # Right: Tool execution metrics
    metrics_names = ["工具调用率", "危险工具率", "DSR"]
    def_vals = [
        m_def.get("tool_call_rate", 0),
        m_def.get("dangerous_tool_rate", 0),
        m_def.get("dsr", 0),
    ]
    none_vals = [
        m_none.get("tool_call_rate", 0),
        m_none.get("dangerous_tool_rate", 0),
        m_none.get("dsr", 0),
    ]
    x2 = np.arange(len(metrics_names))
    w = 0.35
    bars1 = ax2.bar(x2 - w / 2, def_vals, w, color=C_DEFENSE, label="有防御 (via proxy)", edgecolor="white")
    bars2 = ax2.bar(x2 + w / 2, none_vals, w, color=C_NO_DEFENSE, label="无防御 (直连)", edgecolor="white")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(metrics_names, fontsize=10)
    ax2.set_ylim(0, 1.25)
    ax2.set_ylabel("Rate", fontsize=11)
    ax2.set_title("工具执行与防御指标", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(axis="y", alpha=0.3)
    for i in range(3):
        ax2.text(x2[i] - w / 2, def_vals[i] + 0.03, fmt_pct(def_vals[i]), ha="center", fontsize=8)
        ax2.text(x2[i] + w / 2, none_vals[i] + 0.03, fmt_pct(none_vals[i]), ha="center", fontsize=8)

    # Annotation
    ax2.annotate("DeepSeek安全对齐\n拒绝所有攻击", xy=(2, 1.0), fontsize=8, color="gray",
                 ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="#fffbe6", alpha=0.8))
    ax2.annotate("无防御下benign\n工具实际被执行", xy=(0.5, 0.45), xytext=(1.5, 0.7),
                 fontsize=7, color="gray", arrowprops=dict(arrowstyle="->", color="gray"))

    fig.suptitle("实验三：工具滥用防御对照实验", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "exp3.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> exp3.png (per-sample heatmap + tool metrics)")


# ═══════════════════════════════════════════════════════════
# Exp4: RAG poison — 3 configs
# ═══════════════════════════════════════════════════════════

def fig_exp4(data):
    """Per-sample heatmap + N03 FPR case study."""
    k1 = "MANUAL_20260607_235552"  # Config1: Clean + NoDefense
    k2 = "MANUAL_20260607_235553"  # Config2: Poison + NoDefense
    k3 = "MANUAL_20260607_235554"  # Config3: Poison + Defense

    results = [data[k]["results"] for k in (k1, k2, k3)]
    metrics = [data[k]["metrics"] for k in (k1, k2, k3)]

    sample_ids = ["MP01", "MP02", "MP03", "N01", "N02", "N03"]
    sample_labels = ["MP01\n记忆投毒", "MP02\n记忆投毒", "MP03\n记忆投毒", "N01\nAPI查询", "N02\n部署查询", "N03\n安全策略"]
    config_labels = ["Config1\n干净+直连", "Config2\n投毒+直连", "Config3\n投毒+代理"]

    verdict_to_val = {"blocked": 0, "refused": 1, "compromised": 2, "passed": 3}
    val_to_color = {0: "#f5222d", 1: "#fa8c16", 2: "#722ed1", 3: "#52c41a"}
    val_to_label = {0: "Blocked", 1: "Refused", 2: "Compromised", 3: "Passed"}

    matrix = np.zeros((len(sample_ids), 3))
    for ci in range(3):
        for si, sid in enumerate(sample_ids):
            for r in results[ci]:
                if r["id"] == sid:
                    matrix[si, ci] = verdict_to_val.get(r.get("verdict", "passed"), 3)
                    break

    fig = plt.figure(figsize=(14, 6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 1])

    # Left: Per-sample verdict heatmap
    ax1 = fig.add_subplot(gs[0, 0])
    cmap = matplotlib.colors.ListedColormap([val_to_color[i] for i in range(4)])
    im = ax1.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=3)
    ax1.set_xticks(np.arange(3))
    ax1.set_xticklabels(config_labels, fontsize=9)
    ax1.set_yticks(np.arange(len(sample_ids)))
    ax1.set_yticklabels(sample_labels, fontsize=8)
    ax1.set_title("逐样本 Verdict (6 样本 × 3 配置)", fontsize=12, fontweight="bold")
    for si in range(len(sample_ids)):
        for ci in range(3):
            v = int(matrix[si, ci])
            ax1.text(ci, si, val_to_label[v], ha="center", va="center", fontsize=7,
                    color="white" if v in (0, 2) else "black", fontweight="bold")

    # Right: DSR/FPR with N03 annotation
    ax2 = fig.add_subplot(gs[0, 1])
    dsr_vals = [m.get("dsr", 0) for m in metrics]
    fpr_vals = [m.get("fpr", 0) for m in metrics]
    x2 = np.arange(3)
    w = 0.35
    ax2.bar(x2 - w / 2, dsr_vals, w, color=C_DEFENSE, label="DSR", edgecolor="white")
    ax2.bar(x2 + w / 2, fpr_vals, w, color="#ff4d4f", label="FPR", edgecolor="white")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(config_labels, fontsize=9)
    ax2.set_ylim(0, 1.25)
    ax2.set_ylabel("Rate", fontsize=11)
    ax2.set_title("DSR / FPR 对比", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=9, loc="upper left")
    ax2.grid(axis="y", alpha=0.3)
    for i in range(3):
        ax2.text(i - w / 2, dsr_vals[i] + 0.03, fmt_pct(dsr_vals[i]), ha="center", fontsize=9)
        ax2.text(i + w / 2, fpr_vals[i] + 0.03, fmt_pct(fpr_vals[i]), ha="center", fontsize=9)

    # N03 annotation box
    ax2.annotate(
        "N03 FPR=33.3%:\n良性查询的RAG检索上下文\n含投毒片段(curl|sh)\n被代理MI007规则拦截",
        xy=(2, 0.33), xytext=(1.0, 1.05),
        fontsize=8, color="#8c0000",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#fff1f0", edgecolor="#ff4d4f", alpha=0.9),
        arrowprops=dict(arrowstyle="->", color="#ff4d4f", lw=1.5),
    )
    ax2.annotate(
        "Config1=Config2:\n投毒知识库未影响\nLLM行为",
        xy=(1, 0.67), xytext=(0.0, 1.05),
        fontsize=8, color="gray",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f0f0", alpha=0.8),
        arrowprops=dict(arrowstyle="->", color="gray"),
    )

    fig.suptitle("实验四：RAG 投毒防御 — 三配置对比", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "exp4.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> exp4.png (per-sample heatmap + N03 case)")


# ═══════════════════════════════════════════════════════════
# Exp5: Ablation — 5 configs
# ═══════════════════════════════════════════════════════════

def fig_exp5(data):
    """Config × layer heatmap + verdict stack."""
    ablation_keys = [
        "MANUAL_20260606_140807",  # Full
        "MANUAL_20260606_140809",  # -L1
        "MANUAL_20260606_140810",  # -L2
        "MANUAL_20260606_140811",  # -L4
        "MANUAL_20260606_140812",  # All-off
    ]
    config_names = ["Full\n(完整五层)", "-L1\n(关源头)", "-L2\n(关交互)", "-L4\n(关工具)", "All-off\n(全关)"]

    layer_order = ["source_governance", "model_interaction", "memory_control",
                   "tool_constraint", "decision_supervision"]
    layer_labels = ["L1 源头", "L2 交互", "L3 记忆", "L4 工具", "L5 决策"]

    metrics = [data[k]["metrics"] for k in ablation_keys]

    # Build config x layer block count matrix
    block_matrix = np.zeros((5, 5))
    for ci, m in enumerate(metrics):
        ls = m.get("layer_stats", {})
        for li, ln in enumerate(layer_order):
            block_matrix[ci, li] = ls.get(ln, {}).get("blocked", 0)

    # Build verdict distribution per config
    verdicts_per_config = []
    for k in ablation_keys:
        vc = data[k]["metrics"].get("verdict_counts", {})
        va = vc.get("attack", {})
        vb = vc.get("benign", {})
        verdicts_per_config.append({
            "attack_blocked": va.get("blocked", 0),
            "attack_warned": va.get("warned", 0),
            "attack_passed": va.get("passed", 0),
            "benign_warned": vb.get("warned", 0),
            "benign_passed": vb.get("passed", 0),
        })

    fig = plt.figure(figsize=(14, 6))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.2])

    # Left: Config × Layer heatmap
    ax1 = fig.add_subplot(gs[0, 0])
    im = ax1.imshow(block_matrix.T, cmap="YlOrRd", aspect="auto", vmin=0, vmax=np.max(block_matrix))
    ax1.set_xticks(np.arange(5))
    ax1.set_xticklabels(config_names, fontsize=8)
    ax1.set_yticks(np.arange(5))
    ax1.set_yticklabels(layer_labels, fontsize=9)
    ax1.set_title("配置 × 防御层 拦截次数热力图", fontsize=12, fontweight="bold")
    for ci in range(5):
        for li in range(5):
            v = int(block_matrix[ci, li])
            color = "white" if v > np.max(block_matrix) / 2 else "black"
            ax1.text(ci, li, str(v) if v > 0 else "", ha="center", va="center", fontsize=10, color=color, fontweight="bold")
    fig.colorbar(im, ax=ax1, label="拦截次数", shrink=0.8)

    # Right: Verdict stack per config
    ax2 = fig.add_subplot(gs[0, 1])
    x = np.arange(5)
    w = 0.35
    attack_warned = [v["attack_warned"] for v in verdicts_per_config]
    attack_passed = [v["attack_passed"] for v in verdicts_per_config]
    benign_warned = [v["benign_warned"] for v in verdicts_per_config]
    benign_passed = [v["benign_passed"] for v in verdicts_per_config]

    # Attack samples (left half of each pair)
    ax2.bar(x - w / 2, attack_warned, w / 2, color=C_WARNED, label="Attack Warned", edgecolor="white")
    ax2.bar(x - w / 2, attack_passed, w / 2, bottom=attack_warned, color=C_COMPROMISED, label="Attack Passed", edgecolor="white")
    # Benign samples (right half of each pair)
    ax2.bar(x + w / 2, benign_warned, w / 2, color="#91d5ff", label="Benign Warned", edgecolor="white")
    ax2.bar(x + w / 2, benign_passed, w / 2, bottom=benign_warned, color=C_PASSED, label="Benign Passed", edgecolor="white")

    ax2.set_xticks(x)
    ax2.set_xticklabels(config_names, fontsize=8)
    ax2.set_ylabel("样本数 (共 9 条: 6 attack + 3 benign)", fontsize=10)
    ax2.set_title("Attack / Benign Verdict 堆叠", fontsize=12, fontweight="bold")
    ax2.legend(fontsize=7, ncol=2, loc="upper right")
    ax2.grid(axis="y", alpha=0.3)

    # Annotation
    ax2.annotate("-L2: L5级联消失\n但良性全通过", xy=(2, 6), fontsize=8, color="#1677ff",
                 ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="#e6f7ff", alpha=0.8))
    ax2.annotate("All-off:\n全部Pass", xy=(4, 9), fontsize=8, color="gray",
                 ha="center", bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f0f0", alpha=0.8))
    ax2.annotate("DSR=100%\n(仅Warned)", xy=(0, 6.5), fontsize=7, color="gray", ha="center")

    fig.suptitle("实验五：消融实验", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "exp5.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> exp5.png (config-layer heatmap + verdict stack)")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("Loading experiment data...")
    data = load_data()

    print("\nGenerating Exp2 figures...")
    fig_exp2_overview(data)
    fig_exp2_heatmap(data)

    print("\nGenerating Exp3 figure...")
    fig_exp3(data)

    print("\nGenerating Exp4 figure...")
    fig_exp4(data)

    print("\nGenerating Exp5 figure...")
    fig_exp5(data)

    print(f"\nAll figures saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
