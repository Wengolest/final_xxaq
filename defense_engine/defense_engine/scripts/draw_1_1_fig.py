"""Generate 1.1_threat_landscape.png — LLM Agent 安全威胁全景图."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
import os

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei"],
    "font.size": 8.5,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.unicode_minus": False,
})

RED    = "#c62828"; RED_BG    = "#ffebee"
BLUE   = "#1565c0"; BLUE_BG   = "#e3f2fd"
ORANGE = "#e65100"; ORANGE_BG = "#fff3e0"
PURPLE = "#6a1b9a"; PURPLE_BG = "#f3e5f5"
GREEN  = "#2e7d32"
GRAY   = "#757575"; DARK = "#333333"

fig, ax = plt.subplots(figsize=(14, 5.5))
ax.set_xlim(0, 14); ax.set_ylim(0, 5.5); ax.axis("off")

# ── Box helper ───────────────────────────────────────────────
def box(ax, x, y, w, h, text, color, bg, fs=8, subtitle=None):
    rect = mp.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                             facecolor=bg, edgecolor=color, linewidth=1.5, zorder=5)
    ax.add_patch(rect)
    cx, cy = x + w/2, y + h/2
    ax.text(cx, cy + 0.06, text, ha="center", va="center", fontsize=fs,
            fontweight="bold", color=color, zorder=6)
    if subtitle:
        ax.text(cx, cy - 0.26, subtitle, ha="center", va="center", fontsize=fs-2,
                color="#757575", zorder=6)

def arrow(ax, x1, y1, x2, y2, color, lw=1.3, style="-", zorder=3):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=zorder,
                arrowprops=dict(arrowstyle="->", color=color, lw=lw, linestyle=style))

def label(ax, x, y, text, color, fs=7, bold=True, ha="center"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=color)

# ═══════════════════════════════════════════════════════════════
# GRID: Y positions for 4 rows
# ═══════════════════════════════════════════════════════════════
ROWS = [4.5, 3.7, 2.9, 2.1]  # top to bottom
BH = 0.7   # box height
BW = {"left": 2.0, "center": 1.8, "right": 2.8}

# ── LEFT: Attack entry points ────────────────────────────────
L_X, L_W = 0.4, BW["left"]
attacks = [
    ("用户直接输入", "提示注入 · 越狱改写 · 编码混淆"),
    ("RAG 检索源", "知识库投毒 · 网页投毒 · GEO 优化"),
    ("工具 / API 返回值", "返回值投毒 · 供应链投毒"),
    ("长期记忆 · 多轮交互", "多轮对话投毒 · 跨平台协同污染"),
]
for i, (title, sub) in enumerate(attacks):
    y = ROWS[i] - BH/2
    box(ax, L_X, y, L_W, BH, title, RED, RED_BG, fs=8, subtitle=sub)

label(ax, L_X + L_W/2, ROWS[0] + BH/2 + 0.35, "攻击入口", RED, fs=9)

# ── CENTER: Agent components ─────────────────────────────────
C_X, C_W = 3.8, BW["center"]
components = ["Brain\n大模型认知", "Planning\n规划与推理", "Action\n工具执行", "Memory\n记忆系统"]
for i, title in enumerate(components):
    y = ROWS[i] - BH/2
    box(ax, C_X, y, C_W, BH, title, BLUE, BLUE_BG, fs=7.5)

label(ax, C_X + C_W/2, ROWS[0] + BH/2 + 0.35, "LLM Agent 核心架构", BLUE, fs=9)

# ── RIGHT: Threat escalation ─────────────────────────────────
R_X, R_W = 7.2, BW["right"]
threats = [
    ("① 语义污染", "模型输出偏航 · 事实错误\n用户被误导 · 信任崩溃"),
    ("② 逻辑篡改", "任务偏离原始目标\n计划被劫持 · 决策受控"),
    ("③ 控制流劫持", "越权执行系统命令\n数据泄露 · 横向移动"),
    ("④ 级联污染", "跨会话持续影响 · 信念固化\n多 Agent 间传播 · 系统沦陷"),
]
threat_colors = [ORANGE, RED, RED, PURPLE]
threat_bgs    = [ORANGE_BG, RED_BG, RED_BG, PURPLE_BG]
for i, (title, sub) in enumerate(threats):
    y = ROWS[i] - BH/2
    box(ax, R_X, y, R_W, BH + 0.15, title, threat_colors[i], threat_bgs[i], fs=8, subtitle=sub)

label(ax, R_X + R_W/2, ROWS[0] + BH/2 + 0.35, "威胁升级链", PURPLE, fs=9)

# ── Arrows: Left → Center (attack injection) ────────────────
for i in range(4):
    y = ROWS[i]
    arrow(ax, L_X + L_W, y, C_X, y, RED, lw=1.2, style="--")
arrow_labels = ["提示注入", "检索污染", "返回值劫持", "记忆投毒"]
for i, txt in enumerate(arrow_labels):
    y = ROWS[i]
    ax.text(L_X + L_W + 0.45, y + 0.2, txt, ha="center", fontsize=6.5,
            color=RED, fontweight="bold", style="italic")

# ── Arrows: Center → Right (threat escalation) ──────────────
for i in range(4):
    y = ROWS[i]
    arrow(ax, C_X + C_W, y, R_X, y, threat_colors[i], lw=1.4)

# ── Vertical connecting lines between rows ───────────────────
# Show that threats escalate: ①→②→③→④
for i in range(3):
    y1, y2 = ROWS[i] - BH/2 - 0.05, ROWS[i+1] + BH/2 + 0.05
    ax.annotate("", xy=(R_X + R_W/2, y2), xytext=(R_X + R_W/2, y1),
                arrowprops=dict(arrowstyle="->", color=PURPLE, lw=1.0, linestyle=":"),
                zorder=2)
ax.text(R_X + R_W/2 + 0.2, (ROWS[1] + ROWS[2])/2, "逐级\n升级", ha="left", va="center",
        fontsize=6.5, color=PURPLE, fontweight="bold")

# ── BOTTOM: Defense strip ────────────────────────────────────
DEF_Y = 0.6
def_layers = [
    ("L1 源头治理", "#00bcd4"),
    ("L2 模型交互", "#2196f3"),
    ("L3 记忆控制", "#4caf50"),
    ("L4 工具约束", "#ff9800"),
    ("L5 决策监督", "#9c27b0"),
]
def_w = 1.8; def_h = 0.5; def_gap = 0.3
def_total_w = len(def_layers) * def_w + (len(def_layers) - 1) * def_gap
def_start_x = (14 - def_total_w) / 2

for i, (name, color) in enumerate(def_layers):
    dx = def_start_x + i * (def_w + def_gap)
    rect = mp.FancyBboxPatch((dx, DEF_Y), def_w, def_h,
                             boxstyle="round,pad=0.08", facecolor=color + "25",
                             edgecolor=color, linewidth=1.5, zorder=5)
    ax.add_patch(rect)
    ax.text(dx + def_w/2, DEF_Y + def_h/2, name, ha="center", va="center",
            fontsize=8, fontweight="bold", color=color, zorder=6)
    # Arrow between layers
    if i < len(def_layers) - 1:
        ax.annotate("→", xy=(dx + def_w + def_gap/2, DEF_Y + def_h/2),
                    xytext=(dx + def_w, DEF_Y + def_h/2),
                    fontsize=12, color=GRAY, ha="center", va="center",
                    arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.2))

label(ax, 7, DEF_Y - 0.4, "本文防御框架：五层纵深防线（覆盖攻击入口 → Agent 组件 → 威胁升级 全链路）", DARK, fs=7.5)

# ── Title ────────────────────────────────────────────────────
ax.text(7, 5.25, "LLM Agent 安全威胁全景图", ha="center", va="center",
        fontsize=13, fontweight="bold", color=DARK)

# ── Section dividers (vertical dashed lines) ──────────────────
for x in [L_X + L_W + 0.5, C_X + C_W + 0.5]:
    ax.axvline(x=3.3, ymin=0.25, ymax=0.92, color="#e0e0e0", lw=0.8, ls="--", zorder=0)
    ax.axvline(x=6.8, ymin=0.25, ymax=0.92, color="#e0e0e0", lw=0.8, ls="--", zorder=0)

# ── Save ────────────────────────────────────────────────────
os.makedirs("paper_figures", exist_ok=True)
out = os.path.join("paper_figures", "1.1_threat_landscape.png")
fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
print(f"Saved → {out}")
plt.close(fig)
