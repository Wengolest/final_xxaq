# RAG 投毒平台 — 对接说明

本压缩包为 **RAG 知识库 / 检索上下文投毒** 实验平台（与思维链投毒包独立）。

## 1. 平台定位

| 项目 | 说明 |
|------|------|
| 攻击方式 | 向语料库注入毒文档，经检索进入 Agent 上下文 |
| 被测 Agent | **需本机部署** HTTP RAG 服务；或使用包内 **`minimal_http_rag_agent`** |
| 模型 | 各 Agent 自行调用 LLM（平台 `.env` 配 DeepSeek 等） |
| 环境 | 对 Agent 内部 **黑盒/灰盒**；对投毒与评估流程 **白盒** |
| 正式 case | `target_agents/poison_tests/poison_test_cases.yaml`（20 条，8 类 standard_8_types） |

### 八类正式投毒（standard_8_types）

| poison_type | 含义 |
|-------------|------|
| `content_fact_poison` | 虚假事实写入 KB |
| `rule_policy_poison` | 虚假策略/规则 |
| `keyword_retrieval_hijack` | 关键词检索劫持 |
| `semantic_neighbor_poison` | 语义近邻占位 |
| `citation_metadata_spoof` | 引用/元数据伪造 |
| `conflict_evidence_poison` | 冲突证据 |
| `context_boundary_poison` | 上下文边界操纵 |
| `instruction_boundary_poison` | 指令边界（KB 内嵌越权指令） |

毒文档由 `generators/case_driven_generators.py` 按 case 自动生成。

---

## 2. 目录结构

```
rag_poison_platform/
├── target_agents/
│   ├── poison_tests/
│   │   ├── poison_test_cases.yaml   # 20 条 RAG case
│   │   ├── case_loader.py
│   │   └── evaluator.py
│   ├── adapters/                  # HTTP / GitHub RAG 适配
│   ├── scripts/                   # 矩阵 runner、demo、诊断脚本
│   ├── registry.yaml              # 已登记 Agent 路径与 API（需按本机修改）
│   └── bulk_agent_poison_manifest.yaml
├── minimal_http_rag_agent/        # 自带 RAG Agent（推荐试跑）
│   ├── app.py
│   ├── run_server.ps1
│   └── requirements.txt
├── generators/                    # 毒文档生成
├── clean_corpus/                  # 干净语料
├── generated/poison_docs/         # 已生成毒文档（可运行时再生成）
├── targets/agent_security_targets.yaml
├── config/rag_config.yaml
├── evaluators/answer_eval.py
├── utils/
├── results/                       # 示例结果（可选）
├── .env.example
└── README.md
```

**本包不包含**：GitHub 开源 RAG Agent 源码（仅 adapter + 配置模板）。

---

## 3. 环境与依赖

### 3.1 平台侧（跑实验脚本）

- Python 3.10+
- 建议安装：

```powershell
pip install openai python-dotenv pyyaml
```

```powershell
cd D:\rag_poison_platform
copy .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（Agent 与评估也会读取）
```

### 3.2 Agent 侧

**方案 A — 包内 minimal_http_rag_agent（推荐对接验证）**

```powershell
cd D:\rag_poison_platform\minimal_http_rag_agent
.\run_server.ps1
```

- 地址：`http://127.0.0.1:18100`
- 首次运行自动创建 `.venv` 并安装依赖
- API：`GET /health`、`POST /ingest`、`POST /query`、`POST /reset`

**方案 B — 自部署 GitHub / 自研 RAG**

1. 本机 clone 并启动 Agent（HTTP 可访问）  
2. **必须修改** `target_agents/registry.yaml`（或 bulk 相关 yaml）中的：
   - `local_path` → 你的仓库路径  
   - `api_base_url` → 你的服务地址  
   - `chat_endpoint` / `ingest_endpoint` / `request_format` 等  
3. 默认配置中的路径为开发机 `D:\AI\...`，**不解压修改无法对接**

Adapter 会探测常见端点（`/query`、`/ingest`、`/documents` 等），详见 `target_agents/adapters/github_http_rag_adapter.py`。

---

## 4. 运行方式

### 4.1 Self-proof Demo（最小闭环，推荐首次对接）

**终端 1 — 启动 RAG Agent：**

```powershell
cd D:\rag_poison_platform\minimal_http_rag_agent
.\run_server.ps1
```

**终端 2 — 跑 RAG 投毒 demo：**

```powershell
cd D:\rag_poison_platform
python target_agents/scripts/run_self_proof_demo.py --rag-only
```

输出：

- `results/self_proof_rag_demo.csv`
- `results/self_proof_rag_demo.summary.json`

> 注意：`run_self_proof_demo.py` 不带 `--rag-only` 时还会调思维链 runner，**本 RAG 包内无 chain 代码**，`--chain-only` / 完整 demo 需另备 `chain_poison_platform` 包。

### 4.2 Case 驱动正式矩阵（standard_8_types）

Agent 已部署且 registry 已改好后：

```powershell
cd D:\rag_poison_platform
python -m target_agents.scripts.run_poison_case_matrix --scale standard_8_types --agent-ids simple_rag_chatbot
```

- `--agent-ids`：指定 registry 中的 agent id，多个用逗号分隔  
- 输出：`results/github_http_rag_poison_matrix.csv` 及 logs  

### 4.3 模板攻击矩阵（早期 5 类 A–E）

```powershell
python -m target_agents.scripts.run_github_http_rag_poison_matrix --agent-ids simple_rag_chatbot
```

### 4.4 健康检查

```powershell
python target_agents/scripts/probe_agent_api.py
# 或
python target_agents/scripts/run_http_agent_smoke_test.py
```

---

## 5. 对接外部 Agent 检查清单

对接方部署好本机 Agent 后，请逐项确认：

- [ ] Agent HTTP 服务已启动，`GET /health`（或等价）可访问  
- [ ] 支持文档写入（HTTP ingest 或 manifest 配置的 file_kb）  
- [ ] 支持 query/chat 接口，payload 与 `registry.yaml` 一致  
- [ ] Agent 能调用 LLM（OpenAI 兼容 / DeepSeek Key 已配置）  
- [ ] 已修改 `registry.yaml` 中 `local_path`、`api_base_url`、端点字段  
- [ ] 平台根目录 `.env` 已配置 `DEEPSEEK_API_KEY`  
- [ ] 试跑：`run_self_proof_demo.py --rag-only` 或单 agent 的 `--agent-ids` 矩阵  

### registry.yaml 示例（需按本机改写）

```yaml
- id: simple_rag_chatbot
  local_path: D:\your_path\simple-rag-chatbot
  api_base_url: http://127.0.0.1:8001
  chat_endpoint: /query
  ingest_endpoint: /documents
  reset_endpoint: /reset
  http_method: POST
  request_format: question
```

---

## 6. 输出说明

| 输出 | 说明 |
|------|------|
| `results/github_http_rag_poison_matrix.csv` | 主矩阵结果 |
| `results/agent_poison_logs/*.log` | 各 Agent 运行日志 |
| `keyword_hit` / `strict_attack_success` | 评估字段（见 poison_tests/evaluator.py） |
| `poison_retrieved` / `poison_rank` | 毒文档是否被检索及排名 |

正式主结果口径：5 native_http Agent × standard_8_types（对接方复现时以自身 Agent 数量为准）。

---

## 7. 与思维链包的关系

| | 本包（RAG） | 思维链包（`chain_poison_platform`） |
|--|-------------|-------------------------------------|
| 投毒入口 | 知识库 / 检索 | 多步 prompt |
| 是否需要外部 Agent | **是**（或 minimal_http_rag_agent） | **否**（内置 Agent） |
| 测试用例 | `poison_test_cases.yaml` | `agent_chain_poison/cases.py` |
| 评估对象 | 最终答案 + 检索 | 推理轨迹逐步偏移 |

两套平台 **独立压缩、独立运行**；联合答辩可分别演示，或合并目录后跑完整 self-proof。

---

## 8. 本包未打包内容（对接须知）

- GitHub 5 个正式 RAG Agent **源码**（需自行 clone）  
- `minimal_http_rag_agent/.venv`（到目标机后 `run_server.ps1` 重建）  
- 完整历史 CSV / 大体积 logs（可按需另传）  
- `.env` 真实密钥（仅提供 `.env.example`）  

---

## 9. 常见问题

**Q：只有压缩包，不部署 Agent 能跑吗？**  
A：不能跑 RAG 矩阵。可用包内 `minimal_http_rag_agent` 作为被测 Agent 完成 demo。

**Q：自研 Agent 接口不一样怎么办？**  
A：改 `registry.yaml` / `bulk_agent_poison_manifest.yaml`，或扩展 `github_http_rag_adapter.py`。

**Q：和思维链投毒是同一套攻击吗？**  
A：不是。RAG 污染数据层检索；思维链污染多步 prompt。机制不同，评估不同。

**Q：instruction_boundary 和 prompt injection 一样吗？**  
A：语义上接近，但 RAG 版毒藏在 KB 文档里，经检索间接进入 context，不是平台直接改 Agent 内部 prompt。

---

## 10. 联系与版本

- 源码来源：`rag_poison_platform/target_agents/` + generators/corpus/evaluators  
- 打包日期：2026-06（对接交付版）  
- 压缩包名：`rag_poison_platform.zip`
