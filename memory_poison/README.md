# Agent MEMORY 投毒攻击与防御评估插件

基于 [MemoryGraft](https://github.com/Jacobhhy/Agent-Memory-Poisoning) / [AgentPoison](https://github.com/AI-secure/AgentPoison) / [MINJA](https://arxiv.org/abs/2503.03704) 研究的 **MEMORY 专项** 红队评估插件。

> **架构说明**：当前为 **BM25 + SQLite 记忆 Agent 仿真**，非完整 MetaGPT 运行时。四种攻击手段均为 `implementation_tier: simulated` 简化实现；MetaGPT ExperiencePool 同步为可选能力（依赖 llama_index/chromadb）。

## 功能

- **5 个记忆 Agent 仿真**（各含 SQLite + BM25 持久化记忆库 + DeepSeek 推理）
- **24 条主攻击样本** + **6 条 Holdout 样本**（规避签名词）
- **三层防御**（签名过滤 / 信任评分 / 来源溯源）+ 消融实验
- **中性 Prompt**（默认）与 **信任 Prompt**（对照）双模式
- **基线 / 持久污染 / 重复实验** 多种实验模式
- **时间戳子目录** 输出 + `latest.json` 指针

## 目录结构

```text
memory_attack/
├── plugin/
│   ├── agents/                 # 5 个 Agent 仿真
│   ├── attacks/                # 投毒注入器
│   ├── defense/                # 防御模块
│   ├── data/
│   │   ├── attack_samples.json
│   │   └── attack_samples_holdout.json
│   └── results/                # 每次实验独立子目录
├── Agent-Memory-Poisoning/     # 上游 MemoryGraft + MetaGPT
└── run_experiment.py
```

## 快速开始

```powershell
pip install openai rank-bm25
pip install -e Agent-Memory-Poisoning

# 试跑（4 条，自动校验）
python run_experiment.py --pilot

# 全量（先试跑再全量）
python run_experiment.py

# 跳过试跑，全量 + 基线 + Holdout + 消融 + 持久污染对比
python run_experiment.py --skip-pilot-check --baseline --defense-ablation --repeats 1
```

### 常用参数

| 参数 | 说明 |
|------|------|
| `--pilot` | 仅跑 4 条试跑 |
| `--skip-pilot-check` | 跳过试跑直接全量 |
| `--prompt-mode neutral\|trusting` | Prompt 模式（默认 neutral） |
| `--repeats N` | 每条样本重复 N 次 |
| `--persistent` | 持久污染（样本间不 reset） |
| `--baseline` | 额外跑无投毒基线 |
| `--holdout` | 仅跑 Holdout 集 |
| `--defense-ablation` | 对成功样本跑 5 种防御模式 |

## 指标定义

| 指标 | 定义 |
|------|------|
| **攻击成功率** | 检索到毒记忆且（LLM 采纳 或 规则命中） |
| **防御拦截率** | 分母 = **攻击已成功** 的样本数，非全部 24 条 |
| **防御 N/A** | 攻击未成功时 `defense_success = N/A` |
| **基线恶意率** | 无投毒时 Agent 回复含恶意内容的比率（应接近 0%） |

## 已知局限

- `rag_vector_drift`：当前为 BM25，无真实向量漂移
- `schema_spoof`：与普通记忆写入相同，无独立 schema 伪造链路
- `minja_injection`：桥接记忆写入，无多轮渐进污染
- MetaGPT 经验池：已尝试同步，需安装 llama_index/chromadb 才生效

## 结果文件

每次实验输出到 `plugin/results/{YYYYMMDD_HHMMSS}/`：

- `attack_results_full.csv` / `attack_results_pilot.csv`
- `baseline_results_full.csv`（若启用 `--baseline`）
- `defense_ablation.csv`（若启用 `--defense-ablation`）
- `summary.csv` + `summary.json`
- `plugin/results/latest.json` 指向最近一次实验
