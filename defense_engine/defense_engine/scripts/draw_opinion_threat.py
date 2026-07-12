"""v3 — 精确网格布局，固定框宽高，坐标数学保证对齐."""
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

# ── Colors ───────────────────────────────────────────────────
RED    = "#c62828"; RED_BG    = "#ffebee"
ORANGE = "#e65100"; ORANGE_BG = "#fff3e0"
BLUE   = "#1565c0"; BLUE_BG   = "#e3f2fd"
GREEN  = "#2e7d32"; GREEN_BG  = "#e8f5e9"
PURPLE = "#7b1fa2"; PURPLE_BG = "#f3e5f5"
GRAY   = "#9e9e9e"; GRAY_BG   = "#f5f5f5"
DARK   = "#424242"

fig, ax = plt.subplots(figsize=(14, 4))
ax.set_xlim(0, 14); ax.set_ylim(0, 4); ax.axis("off")

# ── Box helper: fixed position, fixed size ───────────────────
def box(ax, x, y, w, h, title, subtitle=None, color=GRAY, bg=None, fs=8):
    """Draw a precisely sized rounded box with centered text."""
    bg = bg or (color + "15")
    rect = mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08",
                             facecolor=bg, edgecolor=color, linewidth=1.5, zorder=5)
    ax.add_patch(rect)
    cx, cy = x + w/2, y + h/2
    ax.text(cx, cy + 0.08, title, ha="center", va="center", fontsize=fs,
            fontweight="bold", color=color, zorder=6)
    if subtitle:
        ax.text(cx, cy - 0.28, subtitle, ha="center", va="center", fontsize=fs-2,
                color="#757575", zorder=6)

def arrow(ax, x1, y1, x2, y2, color, lw=1.2, style="-", zorder=3):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=zorder,
                arrowprops=dict(arrowstyle="->", color=color, lw=lw, linestyle=style))

def curved(ax, x1, y1, x2, y2, color, rad=-0.5, lw=1.2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=2,
                arrowprops=dict(arrowstyle="->", color=color, lw=lw, linestyle="--",
                                connectionstyle=f"arc3,rad={rad}"))

# ═══════════════════════════════════════════════════════════════
# GRID: everything is anchored to these X values
# ═══════════════════════════════════════════════════════════════
# Box definitions: (left_x, width, height, center_y, ...)
# All Y positions are center-aligned on the main row

Y_CENTER = 2.2   # vertical center of main row
BH = 1.8         # standard box height

# ── Column 1: Attacker ───────────────────────────────────────
X1, W1 = 0.5, 2.2
box(ax, X1, Y_CENTER - BH/2, W1, BH, "攻击者\nAttacker", color=RED, bg=RED_BG, fs=9)
ax.text(X1 + W1/2, Y_CENTER - BH/2 - 0.25,
        "GEO 优化 · 注入对抗文档\n批量 AI 软文 · 多平台发布",
        ha="center", va="top", fontsize=6, color=RED, style="italic")
ax.text(X1 + W1/2, Y_CENTER + BH/2 + 0.3, "① 污染注入",
        ha="center", fontsize=7.5, color=RED, fontweight="bold")

# ── Column 3: Agent ─────────────────────────────────────────
X3, W3 = 9.5, 2.0
box(ax, X3, Y_CENTER - BH/2, W3, BH, "LLM Agent", color=BLUE, bg=BLUE_BG, fs=9,
    subtitle="LLM Brain · RAG 检索 · Memory 记忆")
ax.text(X3 + W3/2, Y_CENTER + BH/2 + 0.3, "③ 检索召回\n    污染内容",
        ha="center", fontsize=7.5, color=BLUE, fontweight="bold")

# ── Column 4: User ──────────────────────────────────────────
X4, W4 = 12.5, 1.2
box(ax, X4, Y_CENTER - 0.5, W4, 1.0, "用户\nUser", color=GREEN, bg=GREEN_BG, fs=8.5)
ax.text(X4 + W4/2, Y_CENTER + 0.5 + 0.35, "④ 偏置输出\n    影响认知",
        ha="center", fontsize=7.5, color=GREEN, fontweight="bold")

# ── Column 2: Ecosystem (between Attacker and Agent) ──────
# The gray dashed boundary
ECO_L = X1 + W1 + 0.5   # 3.2
ECO_R = X3 - 0.5         # 9.0
ECO_W = ECO_R - ECO_L    # 5.8
ECO_T = Y_CENTER + BH/2 + 0.1   # 3.1
ECO_B = Y_CENTER - BH/2 - 0.15  # 1.25
ECO_H = ECO_T - ECO_B            # ~1.85
eco_rect = mp.FancyBboxPatch((ECO_L, ECO_B), ECO_W, ECO_H,
    boxstyle="round,pad=0.2", facecolor="#fafafa",
    edgecolor=GRAY, linewidth=1.2, linestyle="--", zorder=1)
ax.add_patch(eco_rect)
ax.text(ECO_L + ECO_W/2, ECO_T + 0.12, "开放信息生态",
        ha="center", va="bottom", fontsize=7.5, fontweight="bold", color=GRAY)

# 4 source boxes in 2×2 inside the ecosystem
# Available interior: ECO_L+0.3 to ECO_R-0.3 horizontally
#                     ECO_B+0.3 to ECO_T-0.3 vertically
inner_l = ECO_L + 0.4; inner_r = ECO_R - 0.4
inner_w = (inner_r - inner_l - 0.5) / 2  # 2 boxes with gap
src_w, src_h = inner_w, 0.6
src_lefts  = [inner_l, inner_l + src_w + 0.5]
src_bottoms = [ECO_T - 0.8, ECO_B + 0.25]

sources = [
    ("搜索引擎检索索引", "GEO 投毒"),
    ("知识库文档向量库", "RAG 投毒"),
    ("新闻 · 百科语料库", "检索偏置"),
    ("第三方 API 返回值", "信念漂移"),
]
src_colors = [ORANGE, ORANGE, ORANGE, ORANGE]
for i in range(4):
    col = i % 2; row = i // 2
    sx = src_lefts[col]; sy = src_bottoms[row]
    box(ax, sx, sy, src_w, src_h, sources[i][0], subtitle=sources[i][1],
        color=ORANGE, bg=ORANGE_BG, fs=6.5)

ax.text(ECO_L + ECO_W/2, Y_CENTER + BH/2 + 0.55, "② 信息生态被污染",
        ha="center", fontsize=7.5, color=ORANGE, fontweight="bold")

# ── Arrows ──────────────────────────────────────────────────
# Attacker → Ecosystem (poison injection, two arrows)
arrow(ax, X1+W1, Y_CENTER+0.25, ECO_L, ECO_T-0.3, RED, style="--")
arrow(ax, X1+W1, Y_CENTER-0.25, ECO_L, ECO_B+0.3, RED, style="--")
ax.text(X1+W1 + (ECO_L-X1-W1)/2, ECO_T+0.85, "注入污染",
        ha="center", fontsize=6.5, color=RED, fontweight="bold", style="italic")

# Ecosystem → Agent (retrieval, two arrows)
arrow(ax, ECO_R, ECO_T-0.3, X3, Y_CENTER+0.25, BLUE)
arrow(ax, ECO_R, ECO_B+0.3, X3, Y_CENTER-0.25, BLUE)
ax.text(ECO_R + (X3-ECO_R)/2, ECO_T+0.55, "检索召回",
        ha="center", fontsize=6.5, color=BLUE, fontweight="bold")

# Agent → User
arrow(ax, X3+W3, Y_CENTER, X4, Y_CENTER, DARK)

# ── Feedback loop ───────────────────────────────────────────
curved(ax, X3+W3/2, Y_CENTER-BH/2, ECO_L+ECO_W/2, Y_CENTER-BH/2-0.35,
       PURPLE, rad=-0.45)
ax.text(ECO_L+ECO_W/2 + 0.5, Y_CENTER-BH/2-1.0,
        "偏置反馈: Agent 输出 → 互联网 → 检索器索引 → Source Bias 自我强化\n"
        "(Dai et al., KDD 2024)",
        ha="center", va="top", fontsize=6, color=PURPLE, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.25", facecolor=PURPLE_BG,
                  edgecolor=PURPLE, linewidth=0.7))

# ── Phase connector arrows (top) ────────────────────────────
phase_x = [X1+W1/2, ECO_L+ECO_W/2, X3+W3/2, X4+W4/2]
for i in range(len(phase_x)-1):
    ax.annotate("", xy=(phase_x[i+1]-1.2, Y_CENTER+BH/2+0.75),
                xytext=(phase_x[i]+0.8, Y_CENTER+BH/2+0.75),
                arrowprops=dict(arrowstyle="->", color="#bdbdbd", lw=0.7))

# ── Save ────────────────────────────────────────────────────
os.makedirs("paper_figures", exist_ok=True)
out = os.path.join("paper_figures", "opinion_poisoning_threat.png")
fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
print(f"Saved → {out}")
plt.close(fig)
