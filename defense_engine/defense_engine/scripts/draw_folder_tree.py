"""Generate 2.5_defense_folder.png — 防御引擎工程目录树."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Consolas", "Courier New"],
    "font.size": 8,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "axes.unicode_minus": False,
})

# ── Build annotated tree ─────────────────────────────────────
# (indent_level, text, color, bold)
# Colors
DIR_COLOR  = "#1565c0"   # blue for directories
CORE_COLOR = "#c62828"   # red for core engine files
LAYER_COLOR = "#e65100"  # orange for layer files
CONFIG_COLOR = "#2e7d32" # green for config/data
TEST_COLOR = "#7b1fa2"   # purple for tests
GRAY = "#9e9e9e"

tree = [
    # Directories (blue, bold)
    (0, "defense_engine/", DIR_COLOR, True),
    (1, "├── config/", DIR_COLOR, True),
    (2, "│   └── defense_rules.json", CONFIG_COLOR, False, "31 条内置规则，SG/MI/MC/TC/DS 五前缀"),
    (1, "├── data/", DIR_COLOR, True),
    (2, "│   └── experiments.json", CONFIG_COLOR, False, "17 条实验记录，含 enriched metrics"),
    (1, "├── agents/", DIR_COLOR, True),
    (2, "│   ├── agent_a_chat.py", GRAY, False, "Agent A · 纯对话 · L1+L2"),
    (2, "│   ├── agent_b_tool.py", GRAY, False, "Agent B · 工具调用 · L1+L2+L4"),
    (2, "│   ├── agent_c_rag.py", GRAY, False, "Agent C · RAG 检索 · L1+L2+L3"),
    (2, "│   ├── agent_langroid_rag.py", GRAY, False, "Agent D · Langroid+ChromaDB"),
    (2, "│   └── agent_smol_tool.py", GRAY, False, "Agent E · Smolagents CodeAgent"),
    (1, "├── tests/", DIR_COLOR, True),
    (2, "│   ├── test_layer1.py", TEST_COLOR, False),
    (2, "│   ├── test_layer2.py", TEST_COLOR, False),
    (2, "│   ├── test_layer3.py", TEST_COLOR, False),
    (2, "│   ├── test_layer4.py", TEST_COLOR, False),
    (2, "│   ├── test_layer5.py", TEST_COLOR, False),
    (2, "│   ├── test_orchestrator.py", TEST_COLOR, False),
    (2, "│   ├── test_rule_engine.py", TEST_COLOR, False),
    (2, "│   ├── test_agent_adapter.py", TEST_COLOR, False),
    (2, "│   └── test_metrics.py", TEST_COLOR, False),
    (1, "├── scripts/", DIR_COLOR, True),
    (2, "│   ├── enrich_experiments.py", GRAY, False),
    (2, "│   └── generate_paper_figures.py", GRAY, False),
    (0, "", DIR_COLOR, False),  # spacer
    (0, "核心引擎（对应表 tab:core_data_structures 四个结构体）", "#333", True),
    (1, "├── defense_types.py", CORE_COLOR, True, "DefenseContext / DefenseRule / LayerCheckResult / DefenseTestResult"),
    (1, "├── orchestrator.py", CORE_COLOR, True, "DefenseOrchestrator · 序贯调度 · 模式决策 · 短路控制"),
    (1, "├── rule_engine.py", CORE_COLOR, True, "RuleEngine · 层前缀过滤 · 优先级排序 · 安全求值"),
    (1, "├── scoring.py", CORE_COLOR, True, "compute_layer_result() · 权重系数（表 tab:layer_weights）"),
    (1, "└── metrics.py", CORE_COLOR, True, "DefenseMetrics · DSR / FPR / FNR / 逐层拦截率"),
    (0, "", DIR_COLOR, False),  # spacer
    (0, "五层防御检测器（§2.5.3–§2.5.7）", "#333", True),
    (1, "├── layer1_source_governance.py", LAYER_COLOR, True, "L1 · 源头治理 · 7 项程序化检测器"),
    (1, "├── layer2_model_interaction.py", LAYER_COLOR, True, "L2 · 模型交互 · 6 项程序化检测器"),
    (1, "├── layer3_memory_control.py", LAYER_COLOR, True, "L3 · 记忆控制 · MemoryBackend 代理架构"),
    (1, "├── layer4_tool_constraint.py", LAYER_COLOR, True, "L4 · 工具约束 · 13 工具四级权限模型"),
    (1, "└── layer5_decision_supervision.py", LAYER_COLOR, True, "L5 · 决策监督 · 熔断·投票·仲裁"),
    (0, "", DIR_COLOR, False),  # spacer
    (0, "集成与接口（§2.5.9–§2.5.10）", "#333", True),
    (1, "├── agent_adapter.py", "#0277bd", True, "DefenseWrapper · 五拦截点零侵入集成"),
    (1, "├── defense_proxy.py", "#0277bd", True, "OpenAI 兼容反向代理 · 端口 8200"),
    (1, "├── mock_agent.py", "#0277bd", True, "MockAgent · 3 角色 · 确定性测试"),
    (1, "└── server.py", "#0277bd", True, "FastAPI 服务 · 端口 8100 · RESTful API"),
    (0, "", DIR_COLOR, False),  # spacer
    (0, "实验与样本（§3）", "#333", True),
    (1, "├── samples.py", GRAY, False, "65 条统一样本 · 20 benign + 45 attack · 9 族 × 5"),
    (1, "├── experiment.py", GRAY, False, "实验一 · 规则引擎基准"),
    (1, "├── experiment_agent.py", GRAY, False, "实验二 · 5 Agent 代理防护"),
    (1, "├── experiment_tool_abuse.py", GRAY, False, "实验三 · 工具滥用对照"),
    (1, "├── experiment_rag_poison.py", GRAY, False, "实验四 · RAG 投毒三配置"),
    (1, "└── experiment_ablation.py", GRAY, False, "实验五 · 消融 5 配置"),
]

# ── Draw ─────────────────────────────────────────────────────
n_lines = len(tree)
line_h = 0.28
fig_h = n_lines * line_h + 1.2
fig, ax = plt.subplots(figsize=(12, fig_h))
ax.set_xlim(0, 12)
ax.set_ylim(0, fig_h)
ax.axis("off")

INDENT = 0.35  # per indent level
y = fig_h - 0.4
x_start = 0.3

for item in tree:
    if len(item) == 4:
        level, text, color, bold = item
        annotation = None
    else:
        level, text, color, bold, annotation = item

    x = x_start + level * INDENT
    weight = "bold" if bold else "normal"
    fs = 8.5 if bold and level == 0 else 7.8

    # Special: section headers (level 0, bold, dark)
    if level == 0 and bold and color == "#333":
        fs = 9
        ax.text(x - 0.1, y, text, fontsize=fs, fontweight="bold", color=color,
                va="center", family="sans-serif")

    # Draw tree line
    if text:
        ax.text(x, y, text, fontsize=fs, fontweight=weight, color=color,
                va="center", family="monospace" if level > 0 else "sans-serif")

    # Annotation in gray
    if annotation and level > 0:
        ax.text(x + len(text) * 0.25 + 0.1, y, "  ← " + annotation,
                fontsize=6.5, color="#757575", va="center", style="italic")

    y -= line_h

# Legend at bottom
legend_y = 0.25
legend_items = [
    (CORE_COLOR, "核心引擎"), (LAYER_COLOR, "五层检测器"),
    ("#0277bd", "集成与接口"), (DIR_COLOR, "目录/配置"),
    (TEST_COLOR, "测试"), (GRAY, "Agent/实验/脚本"),
]
for i, (c, label) in enumerate(legend_items):
    lx = 0.5 + i * 2.0
    ax.plot(lx, legend_y, "s", color=c, markersize=8, clip_on=False)
    ax.text(lx + 0.2, legend_y, label, fontsize=7.5, color="#333", va="center")

ax.text(0.5, legend_y - 0.35,
        "箭头注释（←）标注了每个模块文件在正文中的对应章节和核心职责",
        fontsize=7, color=GRAY, style="italic")

# ── Save ────────────────────────────────────────────────────
outdir = "paper_figures"
os.makedirs(outdir, exist_ok=True)
out = os.path.join(outdir, "2.5_defense_folder.png")
fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
print(f"Saved → {out}")
plt.close(fig)
