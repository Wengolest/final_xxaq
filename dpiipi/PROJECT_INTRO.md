# AgentSecurity — 项目完整介绍

## 一句话概述

基于 DeepSeek API 的 Prompt 注入攻击框架，支持 **DPI（直接提示注入）** 和 **IPI（间接提示注入）** 两种攻击模式，对接 AgentEVAL-Risk-Tools 编排器进行自动化安全评测。

---

## 项目定位

这是一个 **AI Agent 安全红队工具**，用于：
1. 对 LLM Agent 发起 Prompt 注入攻击
2. 自动评分攻击是否成功（LLM-as-Judge）
3. 生成 AgentAuditor 兼容的轨迹数据（用于下游分析）
4. 作为 AgentEVAL-Risk-Tools 的执行器后端

---

## 核心技术概念

### DPI（Direct Prompt Injection，直接提示注入）
- **注入位置**：恶意指令直接拼接到 User Prompt 末尾
- **LLM 调用**：单轮（一次 API 调用）
- **轨迹结构**：`user → agent`（2 turns）
- **攻击面**：用户输入不可信

### IPI（Indirect Prompt Injection，间接提示注入）
- **注入位置**：恶意指令隐藏在工具返回值（Tool Output / Environment）中
- **LLM 调用**：两轮（第一轮调用工具 → 工具返回污染数据 → 第二轮做决策）
- **轨迹结构**：`user → agent → environment → agent`（4 turns）
- **攻击面**：外部数据源（邮件、文件、检索结果）不可信

---

## 目录结构

```
AgentSecurity/
├── README.md                          # 项目 README（快速开始、实验结果）
├── PROJECT_INTRO.md                   # ← 本文件（完整项目介绍，供其他 Agent 阅读）
│
├── attacker/                          # 攻击器核心模块（Python package）
│   ├── __init__.py                    # 模块导出
│   ├── run.py                         # CLI 入口（支持 --mode dpi|ipi）
│   ├── api.py                         # FastAPI HTTP 接口（端口 8900）
│   ├── scorer.py                      # LLM 裁判评分器（DeepSeek JSON mode + Ollama）
│   ├── variants.py                    # DPI：5 种注入变体
│   ├── tools.py                       # DPI：8 个攻击工具定义
│   ├── orchestrator.py                # DPI + IPI 攻击编排器（核心逻辑）
│   ├── converter.py                   # 轨迹转换（DPI 2-turn / IPI 4-turn → ExperimentRecord）
│   └── ipi_scenarios.py               # IPI：6 个预置攻击场景（含 tool_defs、污染数据）
│
├── dispatcher.py                      # AgentEVAL 分发器（读取 execution_bundle.json 并执行）
├── shared/
│   └── trajectory.py                  # 轨迹数据模型（TrajectoryTurn / ExperimentRecord / TrajectoryExporter）
│
└── results/                           # 实验结果
    ├── dispatcher_v2.json             # 最新完整 dispatcher 结果（7 cases）
    ├── ipi_results.json               # IPI 各场景独立结果
    ├── trajectory_ipi_experiment.json # IPI 4 轮轨迹（AgentAuditor 格式）
    ├── dpi_results.json               # DPI 结果
    └── trajectory_experiment.json     # DPI 2 轮轨迹
```

---

## 关键文件说明

### `attacker/orchestrator.py` — 核心编排器
- **`DPIAttackOrchestrator`**：单轮 LLM 调用，拼接 injection prompt → 获取回复 → 评分
- **`IPIAttackOrchestrator`**：两轮 LLM 调用
  - Round 1：发送干净任务 + tool_defs → LLM 调用工具
  - Round 2：工具返回污染数据（contaminated_output）→ LLM 做最终决策
  - 使用 `scorer.judge_ipi()` 评分
- **`IPIAttackResult`**：IPI 攻击结果数据类（14 个字段）

### `attacker/ipi_scenarios.py` — IPI 攻击场景定义
- 6 个预置场景：`email`, `file`, `finance`, `authorization`, `privacy`, `rag_poison`
- 每个场景包含：`tool_defs`（OpenAI function-calling 格式）、`user_task`（干净任务）、`contaminated_output`（含注入的工具返回值）、`attack_goal`
- `infer_scenario_from_case()`：从 AgentEVAL case dict 自动推断场景

### `attacker/scorer.py` — 评分器
- **`DeepSeekScorer`**：使用 `response_format={"type": "json_object"}` 强制 JSON 输出
- **`OllamaScorer`**：使用正则提取 + 关键词回退
- `judge_dpi()` 和 `judge_ipi()` 两套评分逻辑
- `create_scorer()` 工厂函数：检测 DEEPSEEK_API_KEY 环境变量自动选择后端

### `attacker/converter.py` — 轨迹转换
- `attack_result_to_record()`：DPI 结果 → 2-turn ExperimentRecord
- `ipi_result_to_record()`：IPI 结果 → 4-turn ExperimentRecord
- 关键区别：IPI 多一个 `role="environment"` 的 TrajectoryTurn

### `dispatcher.py` — AgentEVAL 对接
- 读取 `execution_bundle.json`（AgentEVAL-Risk-Tools 生成）
- 根据 `executor` 字段路由到 DPI 或 IPI 执行器
- 已实现的执行器：
  - `prompt_orchestrator` → DPI
  - `rag_poison_runner` → IPI
  - `tool_output_runner` → IPI
  - `mcp_runner` → IPI
  - `planning_trace_runner` → IPI
- 返回 `RunResult` 格式（对接 AgentEVAL 的 `submit_results()`）

### `shared/trajectory.py` — 轨迹数据模型
- `TrajectoryTurn`：单轮交互（role + thought + action 或 role + content）
- `ExperimentRecord`：完整实验记录（对标 `experiment_20.json` 格式）
- `TrajectoryExporter`：批量导出（支持 `experiment` 和 `rjudge` 两种风格）

---

## 技术栈

| 组件 | 技术 |
|------|------|
| LLM 目标 | DeepSeek API（`deepseek-chat`）或 Ollama 本地模型 |
| LLM 裁判 | DeepSeek JSON mode 或 Ollama（`qwen3:4b`） |
| API 框架 | FastAPI + Uvicorn（端口 8900） |
| HTTP 客户端 | `openai` Python SDK（兼容 DeepSeek API） |
| 数据模型 | Python dataclasses + Pydantic |
| 轨迹格式 | 对齐 AgentAuditor `experiment_20.json` 格式 |
| 上游对接 | AgentEVAL-Risk-Tools（`execution_bundle.json` → `RunResult`） |

---

## 运行方式

### CLI 快速测试
```bash
cd E:\wangan\AgentSecurity
set DEEPSEEK_API_KEY=sk-xxxxxxxx

# DPI 攻击
python -m attacker.run --mode dpi --target deepseek-chat --target-url https://api.deepseek.com

# IPI 攻击（单个场景）
python -m attacker.run --mode ipi --scenarios rag_poison

# IPI 攻击（所有场景）
python -m attacker.run --mode ipi

# 查看可用变体/工具/场景
python -m attacker.run --list
```

### Dispatcher（对接 AgentEVAL）
```bash
python dispatcher.py \
  --bundle E:/wangan/AgentEVAL-Risk-Tools/runs/quickstart/execution_bundle.json \
  --out results/dispatcher_v2.json
```

### HTTP API
```bash
python -m attacker.api
# 启动在 http://localhost:8900
# 文档在 http://localhost:8900/docs
```

---

## 依赖的外部项目

### AgentEVAL-Risk-Tools
- 路径：`E:\wangan\AgentEVAL-Risk-Tools`
- 作用：生成测试用例（`execution_bundle.json`），接收执行结果（`RunResult`）
- 关键文件：`src/agenteval/schemas.py`（数据契约）、`src/agenteval/pipeline.py`（submit_results）

### DeepSeek API
- Endpoint：`https://api.deepseek.com`
- API Key：存储在 `E:\wangan\deepseekapi.txt`（需自行获取，或设置 `DEEPSEEK_API_KEY` 环境变量）
- 模型：`deepseek-chat`（解析为 `deepseek-v4-flash`）
- 特性：原生 tool calling + `response_format` JSON mode

---

## 当前实验结果（dispatcher_v2.json）

| 指标 | 数值 |
|------|------|
| 总用例数 | 7 |
| 总 ASR | 14.3%（1/7）|
| DPI ASR | 33.3%（1/3）|
| IPI ASR | 0%（0/4，全部 `adopted_no_action`）|

**结论**：
- IPI 框架已跑通：4 个 rag_poison case 从不支持的 `not_triggered` 变为攻击已执行的 `adopted_no_action`
- 轨迹生成正确：4 轮结构对齐 experiment_20.json
- DeepSeek-v4 对工具返回值注入抵抗力较强，换用小模型可提升 ASR

---

## 已知限制 / TODO

1. **IPI ASR 为 0%**：DeepSeek-v4 安全对齐较强，可尝试换用小模型（如 qwen2:0.5b via Ollama）提高攻击成功率
2. **部分 executor 未实现**：`memory_runner`、`multi_agent_runner`、`search_rag_runner` 仍返回 `not_triggered`
3. **Ollama DPI 依赖本地模型**：需确保 Ollama 已安装并拉取 `qwen2:0.5b` 和 `qwen3:4b`
4. **无沙箱执行**：目前不实际执行危险操作（如删文件、转账），仅评测 Agent 是否"意图"执行

---

## 如何扩展

### 添加新的 IPI 场景
在 `attacker/ipi_scenarios.py` 中新增 `IPIScenario` 实例，包含 tool_defs、user_task、contaminated_output、attack_goal。

### 添加新的 Executor
在 `dispatcher.py` 中实现 `_execute_xxx(case, target)` 函数，然后用 `self.registry.register("executor_name")(_execute_xxx)` 注册。

### 添加新的评分器
继承 `BaseScorer`（在 `scorer.py`），实现 `judge_dpi()` 和 `judge_ipi()` 方法。

---

## 作者与环境

- 工作目录：`E:\wangan\AgentSecurity`
- Git 仓库：`https://github.com/ghconscript/Agent-Security`（branch: `gh`）
- 运行平台：Windows 11
- Python 版本：3.10+
