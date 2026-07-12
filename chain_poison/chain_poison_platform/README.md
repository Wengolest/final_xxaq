# Agent 推理链投毒平台 — 对接说明

本压缩包为 **多步 Agent 推理链 prompt 注入投毒** 实验平台（与 RAG 投毒包独立）。

## 1. 平台定位

| 项目 | 说明 |
|------|------|
| 攻击方式 | 中间步骤 **prompt 注入**（`poison_instruction` 拼入 LLM user prompt） |
| Agent | **内置** `AgentChainRunner`，无需对接外部 Agent |
| 模型 | DeepSeek API（OpenAI 兼容接口） |
| 环境 | **白盒**：显式四步 `plan → evidence → decision → final_answer` |
| 测试用例 | 100 条（5 类 × 20），定义于 `agent_chain_poison/cases.py` |

### 五类攻击（poison_type）

| 类型 | 含义 |
|------|------|
| `logical_rule_injection` | 伪逻辑规则（如「无直接损失则不算高风险」） |
| `priority_shift_injection` | 优先级偏移（如「业务连续性优先于安全升级」） |
| `step_order_hijack` | 步骤顺序劫持（先结论后找证据） |
| `evidence_suppression` | 证据压制（关键信号当噪声） |
| `autonomous_action_drift` | 自治动作漂移（未授权自动处置） |

---

## 2. 目录结构

```
chain_poison_platform/
├── agent_chain_poison/
│   ├── cases.py          # 100 条 case（user_task / poison_instruction / injection_step）
│   ├── agent_runner.py   # clean / poisoned 多步执行
│   ├── prompts.py        # 各步 prompt 与注入块 _append_poison_block
│   └── evaluator.py      # reasoning_shift、strict_success 等
├── runners/
│   ├── run_agent_chain_poison.py           # 主入口
│   ├── merge_agent_chain_poison_results.py # 合并多次 CSV
│   └── plot_agent_chain_poison_results.py  # 汇总图
├── utils/                # DeepSeek 环境、.env 加载
├── outputs/              # 示例输出（可选）
├── .env.example
└── README.md
```

---

## 3. 环境与依赖

- Python 3.10+
- 依赖：`openai`、`python-dotenv`

```powershell
pip install openai python-dotenv
```

配置 API Key：

```powershell
cd D:\chain_poison_platform
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

`.env` 示例：

```
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

---

## 4. 运行方式

### 4.1 快速试跑（推荐）

```powershell
cd D:\chain_poison_platform
python -m runners.run_agent_chain_poison --limit 5 --fast
```

- `--fast`：每 case 2 次 LLM 调用（decision + final_answer）
- 不加 `--fast`：标准 4 步，poisoned 复用 clean 的 plan/evidence，共 6 次调用/case

### 4.2 全量 100 case

```powershell
python -m runners.run_agent_chain_poison --fast
# 输出目录默认 outputs/agent_chain_poison/
```

### 4.3 断点续跑

```powershell
python -m runners.run_agent_chain_poison --resume outputs/agent_chain_poison/xxx.csv
```

### 4.4 合并与作图

```powershell
python -m runners.merge_agent_chain_poison_results
python -m runners.plot_agent_chain_poison_results
```

---

## 5. 输出说明

每次运行生成：

| 文件 | 内容 |
|------|------|
| `agent_chain_poison_<时间>_<id>.csv` | 每 case 指标 + 完整轨迹 JSON |
| `*.summary.json` / `*.summary.md` | 汇总统计 |

CSV 关键字段：`reasoning_shift`、`decision_shift`、`strict_success`、`clean_trajectory_json`、`poisoned_trajectory_json`。

默认输出目录：`outputs/agent_chain_poison/`（可通过 `--output-dir` 修改）。

---

## 6. 对接说明（重要）

### 6.1 本包 **不需要** 对接外部 Agent

Agent 即 `agent_chain_poison/agent_runner.py` 中的 `AgentChainRunner`，解压配好 `.env` 即可跑。

### 6.2 本包 **不支持** Plug-in 任意第三方 Agent

当前无 HTTP adapter；若需对接自研多步 Agent，需自行改造 `agent_runner.py` 或新增 adapter。

### 6.3 与 RAG 投毒包的关系

| | 本包（思维链） | RAG 包（`rag_poison_platform`） |
|--|----------------|----------------------------------|
| 投毒对象 | 多步 prompt | 知识库文档 / 检索上下文 |
| 外部 Agent | 不需要 | 需要（或用包内 minimal_http_rag_agent） |
| 联合 demo | — | RAG 包的 `run_self_proof_demo.py --chain-only` 依赖本包代码，**仅 RAG 包无法跑 chain 部分** |

两套平台可并列交付、分别实验；合并 demo 需同时拥有两个包或合并目录。

---

## 7. 投毒机制简述（对接答辩用）

1. `run_clean()`：完整跑四步，得到 clean 轨迹  
2. `run_poisoned()`：复用 clean 的 plan+evidence，在 `injection_step` 对应步骤的 prompt 中追加 `poison_instruction`  
3. `evaluator.py`：对比两条轨迹，计算偏移与 `strict_success`

注入位置（标准模式）：

| injection_step | 毒文本出现在 |
|----------------|--------------|
| `evidence` / `reasoning_summary` | decision + final_answer 的 prompt |
| `decision` | 仅 final_answer 的 prompt |

---

## 8. 常见问题

**Q：没有 DeepSeek Key 能跑吗？**  
A：不能，所有步骤均调用 LLM API。

**Q：和 prompt injection 什么关系？**  
A：机制上就是中间步骤的 prompt injection；「推理链投毒」强调多步轨迹评估与五类污染模式，不是另一种 delivery。

**Q：能否看到模型完整 hidden CoT？**  
A：不能，仅能看到各步结构化 JSON 输出（外显轨迹）。

---

## 9. 联系与版本

- 源码来源：`rag_poison_platform/agent_chain_poison/` + 相关 runners/utils  
- 打包日期：2026-06（对接交付版）  
- 压缩包名：`chain_poison_platform.zip`
