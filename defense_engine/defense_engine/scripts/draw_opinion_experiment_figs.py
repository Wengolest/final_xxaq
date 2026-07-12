"""Generate figures for opinion poisoning quantitative analysis section.
Fig 1: Three-analysis key metrics comparison
Fig 2: Defense coverage gaps across L1-L5 for four attack vectors
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei"],
    "font.size": 9,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.unicode_minus": False,
})

RED    = "#c62828"; BLUE   = "#1565c0"
ORANGE = "#e65100"; GREEN  = "#2e7d32"
PURPLE = "#7b1fa2"; GRAY   = "#757575"

OUT = "paper_figures"
os.makedirs(OUT, exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# Figure 1: Three-analysis key metrics comparison
# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))

# ── Panel A: PoisonedRAG ────────────────────────────────────
ax = axes[0]
labels = ["白盒\nASR", "黑盒\nASR", "多攻击者\n竞争 ASR"]
values = [87.4, 72.9, 7.3]
colors = [RED, ORANGE, GREEN]
bars = ax.bar(labels, values, color=colors, edgecolor="white", width=0.55)
for b, v in zip(bars, values):
    ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1.5,
            f"{v}%", ha="center", fontsize=11, fontweight="bold", color=b.get_facecolor())
ax.set_ylim(0, 105)
ax.set_ylabel("Attack Success Rate (%)", fontsize=9)
ax.set_title("PoisonedRAG\n(Zou et al., 2024)", fontsize=10, fontweight="bold", color="#333")
ax.grid(axis="y", alpha=0.25)
# Annotation
ax.annotate("仅 5 条投毒文本\n投毒率 0.0002%",
            xy=(0, 87.4), xytext=(0.5, 55),
            fontsize=7.5, color=RED, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.2),
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#fff5f5", edgecolor=RED, alpha=0.8))

# ── Panel B: Topic-FlipRAG ──────────────────────────────────
ax = axes[1]
labels = ["立场\n偏移", "用户观点\n偏移", "绕过困惑\n度过滤", "绕过\n改写", "绕过\n重排序"]
values = [50, 16, 100, 90, 80]
colors = [PURPLE, PURPLE, GRAY, GRAY, GRAY]
bars = ax.bar(labels, values, color=colors, edgecolor="white", width=0.55)
for i, (b, v) in enumerate(zip(bars, values)):
    if v >= 90:  # near-100% bars: put label inside, white text
        ax.text(b.get_x() + b.get_width()/2, b.get_height() - 8,
                f"≈{v}%", ha="center", fontsize=10, fontweight="bold", color="white")
    else:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 2,
                f"{v}%", ha="center", fontsize=10, fontweight="bold", color=b.get_facecolor())
ax.set_ylim(0, 115)
ax.set_ylabel("Effectiveness / Evasion Rate (%)", fontsize=9)
ax.set_title("Topic-FlipRAG\n(Gong et al., USENIX Sec'25)", fontsize=10, fontweight="bold", color="#333")
ax.grid(axis="y", alpha=0.25)
# Legend
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=PURPLE, label="攻击效力"),
                   Patch(facecolor=GRAY, label="防御绕过率")]
ax.legend(handles=legend_elements, fontsize=7.5, loc="upper right")

# ── Panel C: Source Bias ────────────────────────────────────
ax = axes[2]
models = ["Contriever\n(一阶段)", "BGE\n(一阶段)", "RankLLaMA\n(二阶段)"]
# Qualitative → quantitative mapping for visualization
bias_levels = [0.85, 0.80, 0.65]  # estimated from paper descriptions
colors = [ORANGE, ORANGE, "#ff9800"]
bars = ax.barh(models, bias_levels, color=colors, edgecolor="white", height=0.5)
for b, v in zip(bars, bias_levels):
    ax.text(b.get_width() + 0.02, b.get_y() + b.get_height()/2,
            "LLM文本\n优先", ha="left", va="center", fontsize=8.5,
            fontweight="bold", color=ORANGE)
ax.set_xlim(0, 1.15)
ax.set_xlabel("LLM 文本偏好程度（估值）", fontsize=9)
ax.set_title("Source Bias\n(Dai et al., KDD 2024)", fontsize=10, fontweight="bold", color="#333")
ax.axvline(x=0.5, color=GRAY, linestyle="--", linewidth=0.8, alpha=0.5)
ax.text(0.51, 2.7, "← 随机水平 (0.5)", fontsize=7, color=GRAY, va="center")
# Annotation — placed in empty lower-right, arrow points up to bars
ax.annotate("偏置在不同检索器\n架构间普遍存在\n且经重排序无法消除",
            xy=(0.85, 1.7), xytext=(0.82, 0.35),
            fontsize=7.5, color=ORANGE, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.2),
            bbox=dict(boxstyle="round,pad=0.25", facecolor="#fff8e1", edgecolor=ORANGE, alpha=0.9))

fig.suptitle("舆论投毒与检索偏置：三组已发表文献的核心定量结果",
             fontsize=12, fontweight="bold", y=1.01)
plt.tight_layout()
p1 = os.path.join(OUT, "opinion_three_analyses.png")
fig.savefig(p1, dpi=300, bbox_inches="tight", facecolor="white")
print(f"Saved → {p1}")
plt.close(fig)

# ═══════════════════════════════════════════════════════════════
# Figure 2: Defense coverage gaps — radar-style bar chart
# ═══════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 4.5))

layers = ["L1 源头", "L2 交互", "L3 记忆", "L4 工具", "L5 决策"]
# Coverage score: 3=experimentally verified, 2=mechanism-based, 1=hypothesis, 0=gap
vectors = {
    "GEO 投毒":      [2, 1, 2, 0, 1],
    "RAG 投毒":      [3, 2, 3, 0, 2],
    "检索偏置":      [2, 1, 1, 0, 2],
    "信念漂移":      [1, 1, 2, 0, 2],
}
x = np.arange(len(layers))
w = 0.2
colors_v = [RED, BLUE, ORANGE, PURPLE]

for i, (name, scores) in enumerate(vectors.items()):
    bars = ax.bar(x + i * w, scores, w, label=name, color=colors_v[i], edgecolor="white")

ax.set_xticks(x + w * 1.5)
ax.set_xticklabels(layers, fontsize=9)
ax.set_ylabel("覆盖充分性评分", fontsize=9)
ax.set_ylim(0, 3.8)
ax.set_yticks([0, 1, 2, 3])
ax.set_yticklabels(["0\n缺口", "1\n待验证\n假设", "2\n机理推理\n覆盖", "3\n实验\n验证"])
ax.legend(fontsize=7.5, ncol=4, loc="upper right")
ax.grid(axis="y", alpha=0.25)
ax.set_title("四类舆论投毒攻击向量在五层防御中的覆盖充分性",
             fontsize=10, fontweight="bold")

# Annotations
ax.annotate("L4 对检索类攻击\n普遍无覆盖",
            xy=(3, 0.1), xytext=(2.3, 0.8),
            fontsize=7.5, color=GRAY, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=GRAY, lw=1),
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#f5f5f5", edgecolor=GRAY, alpha=0.8))
ax.annotate("RAG 投毒\n已有实验验证",
            xy=(1.5, 3), xytext=(0.3, 3.4),
            fontsize=7.5, color=GREEN, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1),
            bbox=dict(boxstyle="round,pad=0.2", facecolor="#e8f5e9", edgecolor=GREEN, alpha=0.8))

plt.tight_layout()
p2 = os.path.join(OUT, "opinion_defense_coverage.png")
fig.savefig(p2, dpi=300, bbox_inches="tight", facecolor="white")
print(f"Saved → {p2}")
plt.close(fig)
