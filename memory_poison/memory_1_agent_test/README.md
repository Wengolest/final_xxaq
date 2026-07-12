# 单 Agent MEMORY 投毒验证实验

> 目的：用 **1 个 Agent + 36 条样本** 证明 MEMORY 投毒真实发生——毒记忆写入 **SQLite 数据库**，经 **BM25 检索** 进入 Agent 上下文，并改变回复。

与主实验 `plugin/` 并列，本目录自包含验证代码与结果；核心 Agent/注入/评估逻辑复用上级 `plugin` 模块。

---

## 一、主实验（出论文结果的那次）说明

### 用了哪些脚本

| 步骤 | 文件路径 | 作用 |
|------|----------|------|
| **总入口** | `run_experiment.py` | 命令行调度试跑/全量/基线/消融 |
| 实验编排 | `plugin/runner.py` | 5 Agent 循环、投毒、评估、导出 |
| 攻击样本 | `plugin/data/attack_samples.json` | 24 条主样本 |
| Holdout | `plugin/data/attack_samples_holdout.json` | 6 条 |
| 投毒注入 | `plugin/attacks/injector.py` | 写 SQLite + 可选 MetaGPT 池 |
| 5 个 Agent | `plugin/agents/*.py` | 各 Agent 记忆库与 Prompt |
| 记忆库 | `plugin/memory/bm25_store.py` | SQLite + BM25 |
| LLM | `plugin/llm_client.py` | DeepSeek 调用 |
| 评估 | `plugin/evaluator.py` | 攻击/基线/防御判定 |
| 防御 | `plugin/defense/defender.py` | 三层过滤 |
| CSV 导出 | `plugin/csv_exporter.py` | 中英列名 CSV |
| 配置 | `plugin/config.py` | API、路径、阈值 |

### 规模（最终主结果 run）

| 项目 | 数值 |
|------|------|
| Agent 数 | **5** |
| 攻击样本 | **24** case |
| 重复次数 | **3** |
| 总记录 | **72** 条 |
| Prompt | neutral |
| 结果目录 | `plugin/results/20260608_212010/` |

### 主实验复现（逐条终端命令）

```powershell
cd D:\MYHIT\MYHIT_DAY\临时文件\memory_attack

pip install openai rank-bm25
pip install -e Agent-Memory-Poisoning

python run_experiment.py --pilot
python run_experiment.py --skip-pilot-check --repeats 3
python run_experiment.py --skip-pilot-check --repeats 3 --baseline --defense-ablation
```

---

## 二、本目录小验证实验

| 项目 | 数值 |
|------|------|
| Agent | **1 个**：`ci_pipeline_agent` |
| 样本 | **36 条** |
| 记忆库 | `agent_databases/ci_pipeline_agent_memory.db` |
| 输出 | `results/validation_*.csv` + `.json` |

### MEMORY 投毒证明字段

- `poison_rows_in_db`：SQLite 中毒记忆行数
- `baseline_poison_retrieved`：投毒前应 false
- `poison_retrieved`：投毒后应 true
- `memory_poison_proven`：入库且检索同时成立

---

## 三、运行步骤

```powershell
cd D:\MYHIT\MYHIT_DAY\临时文件\memory_attack
pip install openai rank-bm25

python memory_1_agent_test/run_validation.py --pilot 5
python memory_1_agent_test/run_validation.py
python memory_1_agent_test/run_validation.py --no-baseline
```

### 预计时间

| 模式 | 预计 |
|------|------|
| `--pilot 5` | 3–5 分钟 |
| 全量 36 条（含基线） | 20–35 分钟 |
| `--no-baseline` | 12–20 分钟 |
