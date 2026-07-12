"""Generate opinion_attack_taxonomy.png — 四类舆论投毒攻击向量分类图."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
import os

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei"],
    "font.size": 8,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.unicode_minus": False,
})

RED    = "#c62828"; RED_BG    = "#ffebee"
BLUE   = "#1565c0"; BLUE_BG   = "#e3f2fd"
ORANGE = "#e65100"; ORANGE_BG = "#fff3e0"
PURPLE = "#6a1b9a"; PURPLE_BG = "#f3e5f5"
GREEN  = "#2e7d32"; GREEN_BG  = "#e8f5e9"
GRAY   = "#9e9e9e"; DARK = "#333333"

fig, ax = plt.subplots(figsize=(11.5, 5.2))
ax.set_xlim(-0.3, 11.5); ax.set_ylim(0, 5.2); ax.axis("off")

def rbox(ax, x, y, w, h, title, color, bg, fs=7.5, lines=None):
    rect = mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                             facecolor=bg, edgecolor=color, linewidth=1.4, zorder=5)
    ax.add_patch(rect)
    ax.text(x + w/2, y + h - 0.2, title, ha="center", va="top", fontsize=fs,
            fontweight="bold", color=color, zorder=6)
    if lines:
        for i, line in enumerate(lines):
            ax.text(x + w/2, y + h - 0.48 - i*0.2, line, ha="center", va="top",
                    fontsize=6, color="#555555", zorder=6)

def arrow(ax, x1, y1, x2, y2, color, lw=1.3, style="-", zorder=3):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=zorder,
                arrowprops=dict(arrowstyle="->", color=color, lw=lw, linestyle=style))

# ═══════════════════════════════════════════════════════════════
# LAYOUT: 2×2 grid of attack vectors
# ═══════════════════════════════════════════════════════════════
# 4 boxes in 2×2, then an Agent box on the right receiving all attacks

BX, BY = 0.3, 0.7     # grid origin
BW, BH = 3.5, 1.5     # box size (shrunk from 4.2×1.7)
GAP_X, GAP_Y = 0.5, 0.35

positions = [
    (BX, BY + BH + GAP_Y),           # top-left
    (BX + BW + GAP_X, BY + BH + GAP_Y),  # top-right
    (BX, BY),                         # bottom-left
    (BX + BW + GAP_X, BY),            # bottom-right
]

boxes = [
    (RED, RED_BG, "GEO 生成式引擎优化投毒",
     ["攻击目标: 搜索引擎 → LLM 检索-生成管道",
      "典型方法: 网页植入统计特征、权威术语、关键词密度优化",
      "代表工作: GEO (Aggarwal et al., 2024)"]),
    (ORANGE, ORANGE_BG, "RAG 知识库投毒",
     ["攻击目标: RAG 检索召回 → LLM 生成输出",
      "典型方法: 向量库注入对抗文档，梯度优化触发短语",
      "代表工作: PoisonedRAG · Topic-FlipRAG · Phantom"]),
    (PURPLE, PURPLE_BG, "检索偏置利用",
     ["攻击目标: 检索排序 → 信息多样性 → 用户认知",
      "典型方法: 批量生成 AI 软文淹没人类原创信息",
      "代表工作: Source Bias (Dai et al., KDD 2024)"]),
    (GREEN, GREEN_BG, "跨平台信念漂移",
     ["攻击目标: Agent 长期记忆 → 多轮决策 → 价值判断",
      "典型方法: 多平台·多模态·长周期协同发布虚假共识",
      "代表工作: BRRA (Wang et al., 2025) · CtrlRAG"]),
]

for i, ((bx, by), (color, bg, title, lines)) in enumerate(zip(positions, boxes)):
    rbox(ax, bx, by, BW, BH, title, color, bg, fs=8.5, lines=lines)
    # Label: attack vector number
    ax.text(bx + 0.15, by + BH - 0.25, f"攻击向量 {i+1}", fontsize=7,
            color=color, fontweight="bold", style="italic", zorder=6)

# ── Agent box (right side, spanning both rows) ────────────────
AX_X = BX + 2*BW + GAP_X + 0.9
AX_W = 1.5
AX_Y_top = BY + BH + GAP_Y + BH
AX_H = 2*BH + GAP_Y

rbox(ax, AX_X, BY, AX_W, AX_H, "", BLUE, BLUE_BG, fs=8)
cy = BY + AX_H/2
ax.text(AX_X + AX_W/2, cy + 0.4, "LLM\nAgent", ha="center", va="center",
        fontsize=10, fontweight="bold", color=BLUE, zorder=6)
ax.text(AX_X + AX_W/2, cy - 0.5, "Brain · RAG\nMemory · Tools", ha="center", va="center",
        fontsize=6.5, color=BLUE, zorder=6, alpha=0.7)

# ── Arrows from each box to Agent ────────────────────────────
for (bx, by) in positions:
    # Arrow from right edge of each box to left edge of Agent
    start_x = bx + BW
    start_y = by + BH/2
    end_x = AX_X
    end_y = start_y
    arrow(ax, start_x, start_y, end_x, end_y, GRAY, lw=1.0)

# ── Large information ecosystem label (background) ───────────
eco = mp.FancyBboxPatch((BX - 0.25, BY - 0.25), 2*BW + GAP_X + 0.5,
                        2*BH + GAP_Y + 0.5,
                        boxstyle="round,pad=0.25", facecolor="none",
                        edgecolor=GRAY, linewidth=1.0, linestyle="--", zorder=0)
ax.add_patch(eco)
eco_cx = BX + BW + GAP_X/2
eco_top = BY + 2*BH + GAP_Y
ax.text(eco_cx, eco_top + 0.35, "开放信息生态 (Open Information Ecosystem)",
        ha="center", va="bottom", fontsize=8, fontweight="bold", color=GRAY)

# ── Attack flow annotation ────────────────────────────────────
mid_x = (eco_cx + AX_X + AX_W/2) / 2
ax.text(eco_cx, eco_top + 0.7, "污染注入", ha="center",
        fontsize=6.5, color=GRAY, style="italic")
ax.text(AX_X + AX_W/2, eco_top + 0.7, "检索/召回", ha="center",
        fontsize=6.5, color=GRAY, style="italic")

# ── Title ────────────────────────────────────────────────────
ax.text(5.75, 5.0, "叙事操控与检索偏置：四类攻击向量分类",
        ha="center", fontsize=11, fontweight="bold", color=DARK)

# ── Legend for defense layers ─────────────────────────────────
legend_y = 0.15
def_layers = [
    ("L1 源头治理", "#00bcd4"), ("L2 模型交互", "#2196f3"),
    ("L3 记忆控制", "#4caf50"), ("L4 工具约束", "#ff9800"), ("L5 决策监督", "#9c27b0"),
]
ax.text(5.75, legend_y + 0.22, "主要防御层映射:",
        ha="center", fontsize=7.5, fontweight="bold", color=DARK)
for i, (name, color) in enumerate(def_layers):
    lx = 2.2 + i * 1.9
    ax.plot(lx, legend_y, "s", color=color, markersize=7, zorder=6)
    ax.text(lx + 0.22, legend_y, name, fontsize=6.5, color=DARK, va="center")

layer_map_text = "GEO投毒→L1+L3    RAG投毒→L1+L3    检索偏置→L1+L5    信念漂移→L3+L5"
ax.text(5.75, legend_y - 0.22, layer_map_text, ha="center", fontsize=6.5, color=GRAY)

# ── Save ────────────────────────────────────────────────────
os.makedirs("paper_figures", exist_ok=True)
out = os.path.join("paper_figures", "opinion_attack_taxonomy.png")
fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
print(f"Saved → {out}")
plt.close(fig)
