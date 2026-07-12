# Defense Engine — LLM Agent 五层纵深防御框架

面向大语言模型智能体的分层安全防护系统，沿 Agent 执行流程部署 **源头治理 → 模型交互 → 记忆控制 → 工具约束 → 决策监督** 五层独立检测器，综合程序化正则检测、可配置规则引擎与风险评分机制，以毫秒级响应拦截提示注入、记忆投毒、工具劫持等攻击向量。

---

## 1. 项目做了什么？

### 目的

LLM Agent 的攻击面超越传统单轮对话——提示注入可在输入层操纵模型行为，RAG 知识库投毒可将恶意指令伪装为检索结果，长期记忆投毒可通过跨会话的持久污染持续偏转 Agent 决策，工具返回值劫持可将语义攻击转化为实际的系统破坏。现有安全方案（如 NeMo Guardrails、Llama Guard）本质上只做输入输出的单点文本审查，无法覆盖 Agent 特有的记忆系统和工具执行层。

本框架的**核心目的**：在 Agent 数据处理流程的**五个结构性转换点**上各部署一层独立的安全检测器，通过层间的信任度连续衰减和风险累积机制，实现对"分步渗透、跨组件传播"的复合攻击的有效拦截，同时以 STRICT/BALANCED/PERMISSIVE 三种安全模式适配不同业务场景对安全性与可用性的差异化权衡。

### 运行流程

```
用户输入
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  DefenseWrapper (透明适配层)                              │
│                                                          │
│  A. wrap_input      → L1 (源头治理) + L2 (模型交互)       │
│     ├── L1: 来源白名单 / 零宽字符 / 伪系统指令 /           │
│     │        编码混淆 / RTL覆盖 / 内容重复                 │
│     └── L2: 危险分隔符 / 指令混淆 / 敏感行为 /             │
│            上下文越权 / PII检测 / 上下文长度               │
│                          │                               │
│                          ▼                               │
│  Agent 处理 ──→ 可能触发工具调用 / 记忆操作               │
│     │                    │          │                    │
│     │    B. wrap_tool   C1/C2. wrap_memory              │
│     │    call → L4       write/read → L3                │
│     │    (工具约束)       (记忆控制)                      │
│     │                    │          │                    │
│     ▼                    ▼          ▼                    │
│  D. wrap_output    → L2 (PII复检) + L5 (决策监督)        │
│     └── L5: 熔断保护 / 跨层交叉验证 / 审计复核 /          │
│             异常行为检测 / 最终仲裁                        │
│                                                          │
│  产出: GuardedResponse (success / action / risk_score)   │
└─────────────────────────────────────────────────────────┘
```

五层逐次执行，层间传递 **trust_level**（信任度从 1.0 开始逐层衰减）和 **risk_score**（各层独立风险评分累加）。编排器根据三种安全模式决定是否短路提前终止。

### 打分标准

每层检测器产出 **CheckFlag** 列表（`block` / `warn` / `log` / `pass`），通过统一评分函数 `compute_layer_result()` 计算该层的归一化风险评分 $r_i \in [0, 1]$：

| 检测来源 | block 级权重 | warn 级权重 | 说明 |
|----------|-------------|------------|------|
| 程序化检测器命中 | 0.25--0.30 | 0.08--0.10 | 各层权重不同，L4 工具层最高 |
| 规则引擎命中 | 0.30--0.35 | 0.10--0.12 | 规则 block/quarantine 命中权重略高于程序化 |
| AI 语义检测 (预留) | 0.40 | 0.15 | 当前未接入真实 ML 模型，使用 PassThroughScorer 占位 |

**信任度衰减**：$\text{trust}_{\text{new}} = \max(0.0, \text{trust}_{\text{in}} - r_i)$

**累积风险**：$\text{cumulative\_risk} = \min(1.0, \sum r_i)$

**三种模式的拦截判定**：

| 模式 | 拦截条件 | 适用场景 |
|------|---------|---------|
| STRICT | 任一层返回 block/quarantine → 立即短路 | 金融交易、关键基础设施 |
| BALANCED (默认) | 累积风险 ≥ 0.7 → 拦截 | 企业办公、智能客服 |
| PERMISSIVE | 仅 block 动作短路 | 创意写作、学术研究 |

BALANCED 阈值 0.7 的设计依据：需至少 3 个独立层产生显著检测信号（$3 \times 0.25 = 0.75 > 0.7$）才会触发拦截，有效降低单层误报导致的非必要阻断。

### 已设计但未实现的大模型判断模块

以下列出框架中理论上需要接入大语言模型 / ML 模型进行语义判断、但当前仅为预留接口或占位实现的全部函数。所有这些函数的**调用链已铺好**（接口 → 权重 → 评分分支 → 规则模式），仅缺少一个真实 ML 模型的实现。

#### 跨层基础设施（scoring.py / rule_engine.py）

| # | 文件:行号 | 函数 / 字段 | 需要大模型做什么 | 当前行为 |
|---|----------|------------|----------------|---------|
| 1 | `scoring.py:197-249` | `SemanticScorer` (ABC) | 对输入/输出/记忆内容做语义安全分类（注入/越狱/投毒等） | 抽象基类，唯一的子类是下方的 PassThroughScorer |
| 2 | `scoring.py:252-274` | `PassThroughScorer.score()` | 调用 Llama Guard 3 / Prompt Guard / 自训练分类模型 | **永远返回 safe**（severity="log"），且未被任何层 import |
| 3 | `scoring.py:38-39` | `LayerWeights.semantic_block` (0.40) / `semantic_warn` (0.15) | 累积 ML 语义检测命中的风险分 | **从未被触发** — PassThroughScorer 只产生 "log" 级别 |
| 4 | `scoring.py:140-145` | `compute_layer_result()` 的 `source=="semantic"` 分支 | 将 ML 检测的 block/warn 转为风险分 | **死代码** — 无任何 CheckFlag 的 source="semantic" 且 severity≠"log" |
| 5 | `rule_engine.py:154-156` | `_match_rule()` 的 `pattern_type=="semantic"` 分支 | 委托外部 ML 分类器做规则条件匹配 | **硬编码 `return False`** — 永不做匹配 |

> 接入方式：写一个 `class LlamaGuardScorer(SemanticScorer)` 实现 `score()` 方法，然后在各层 `evaluate()` 中调用 `self.scorer.score(content)` 并将返回的 CheckFlag 传入 flags 列表。整条链路会自动贯通。

#### L3 记忆控制层（layer3_memory_control.py）

| # | 文件:行号 | 函数 / 字段 | 需要大模型做什么 | 当前行为 |
|---|----------|------------|----------------|---------|
| 6 | `layer3_memory_control.py:77-111` | `MemoryBackend` (ABC) | 对接真实记忆后端（ChromaDB / FAISS / Mem0 / LangGraph） | 仅有 `SimulatedMemoryBackend`（内存 dict，进程重启即丢） |
| 7 | `layer3_memory_control.py:133-140` | `SimulatedMemoryBackend.search()` | 基于向量嵌入的语义检索 | **子字符串大小写匹配** |
| 8 | `layer3_memory_control.py:187-198` | `_detect_conflict()` | 用嵌入模型 / LLM 判断两条记忆是否语义矛盾 | **4 组硬编码中文关键词极性对比**（允许↔禁止 等），无法检测委婉表达或英文冲突 |

#### L5 决策监督层（layer5_decision_supervision.py）

| # | 文件:行号 | 函数 / 字段 | 需要大模型做什么 | 当前行为 |
|---|----------|------------|----------------|---------|
| 9 | `layer5_decision_supervision.py:243-268` | `_check_anomaly()` | 建立行为基线模型，检测风险分斜率 / 模式突变等异常 | **简单阈值比较**：高风险比例 > 50% 或新增 flag 类型 > 3 即告警 |
| 10 | `layer5_decision_supervision.py:186-225` | `_check_cross_validation()` | 当各层意见分歧时，用 LLM 做语义一致性分析判断谁对 | **纯计数投票**：统计 block/warn/pass 数量和比例，与阈值比较 |

#### 汇总

```
        跨层 (5 项)          L3 (3 项)          L5 (2 项)
        ┌──────────┐       ┌──────────┐       ┌──────────┐
        │SemanticScorer│   │MemoryBackend│    │_check_anomaly│
        │PassThroughScorer│ │search()    │    │_check_cross_validation│
        │semantic 权重  │   │_detect_conflict│  │          │
        │compute 语义分支│   │           │       │          │
        │_match semantic│    │           │       │          │
        └──────────┘       └──────────┘       └──────────┘
        无 ML = 语义检测     无 ML = 无生产级     无 ML = 统计粗糙
        整条链路空转         记忆后端              无内容理解
```

**L1 / L2 / L4 三层无此类问题** — 它们防护的攻击向量（零宽字符、编码混淆、危险分隔符、高危命令模式）具有确定的字节/正则特征，不需要语义理解，当前实现已完备。

---

## 2. 如何运行？

### 环境要求

```
Python 3.10+
```

### 安装依赖

```bash
cd defense_engine
pip install -r requirements.txt
```

依赖包（仅 3 个）：`fastapi`、`uvicorn`、`pydantic`。核心防御引擎零外部依赖。

### 运行方式

**方式一：快速测试（单样本）**

```bash
python ATEST.py
```

直接用 DefenseOrchestrator 送一条攻击样本，打印 passed 和 risk_score。

**方式二：演示脚本（7 个内置样本）**

```bash
python demo.py
```

依次展示：正常请求、提示注入、越狱+零宽字符、上下文越权、PII 泄露、记忆投毒、多层组合攻击。每个样本逐层打印检测结果。

**方式三：端到端演示（MockAgent + DefenseWrapper + 指标报告）**

```bash
python demo_end_to_end.py
```

覆盖正常交互、注入攻击、记忆投毒、高危工具调用、PII/信息泄露、组合攻击 6 类场景，最终输出完整的指标报告。

**方式四：HTTP API 服务（生产级）**

```bash
uvicorn server:app --host 0.0.0.0 --port 8100
```

启动后访问 `http://localhost:8100/docs` 查看 Swagger 交互文档。核心端点：

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/defenses/layers` | 获取五层完整配置 |
| PUT | `/api/defenses/config` | 更新层启用状态或参数 |
| POST | `/api/defenses/rules` | 添加自定义规则 |
| PUT/DELETE | `/api/defenses/rules/{rule_id}` | 更新/删除规则 |
| POST | `/api/defenses/test` | 提交内容执行五层检测 |
| GET | `/api/defenses/stats` | 获取累计统计指标 |
| GET | `/api/defenses/strategies` | 获取五种预设策略 |
| PUT | `/api/defenses/strategies/{name}/apply` | 一键切换策略 |

**运行全部测试（251 项）：**

```bash
python run_tests.py
```

---

## 3. 输出是什么？

### DefenseOrchestrator.run() → DefenseTestResult

| 字段 | 类型 | 含义 |
|------|------|------|
| `passed` | bool | 是否放行 |
| `final_action` | str | `"passed"` / `"blocked"` / `"warned"` |
| `risk_score` | float | 累积风险评分 0.0--1.0 |
| `layer_results` | dict | 各层详情，短路层为 null |
| `processing_time_ms` | float | 总耗时 |

每层的 LayerCheckResult 包含：

| 字段 | 含义 |
|------|------|
| `passed` | 该层是否通过 |
| `action` | pass / warn / block / quarantine |
| `flags` | 具体检测标记列表，如 `[L1-zero_width_chars] blocked: detected U+200B` |
| `matched_rules` | 命中的规则 ID 列表 |
| `risk_score` | 该层独立风险评分 |
| `trust_level` | 该层衰减后的信任度 |

### DefenseWrapper → GuardedResponse

| 字段 | 含义 | 示例 |
|------|------|------|
| `success` | 是否放行 | `False` = 被拦截 |
| `action` | 处置动作 | `"pass"` / `"warn"` / `"block"` |
| `blocked_by` | 拦截层 | `"source_governance"` |
| `blocked_reason` | 拦截原因 | `"detected zero-width character U+200B"` |
| `risk_score` | 风险评分 | `0.25` |
| `original_response` | Agent 原始响应 | 未拦截时包含 |
| `elapsed_ms` | 耗时 | `15.3` |

**`blocked_by` 值与防御层的对应关系：**

| `blocked_by` 值 | 对应层 | 含义 |
|-----------------|--------|------|
| `source_governance` | **L1** 源头治理 | 伪系统指令、零宽字符、编码混淆、来源白名单等在输入阶段即被拦截 |
| `model_interaction` | **L2** 模型交互 | 敏感行为关键词、指令混淆、危险分隔符等在输入/输出审查时被拦截 |
| `memory_control` | **L3** 记忆控制 | 记忆写入风险检测、来源信任不足、冲突检测触发拒绝写入 |
| `tool_constraint` | **L4** 工具约束 | 工具不在白名单、危险参数匹配、敏感路径访问、频率超限 |
| `decision_supervision` | **L5** 决策监督 | 熔断器打开、跨层交叉验证投票触发、累积风险超审计阈值 |
| `input` | 输入阶段（L1+L2） | 在输入拦截点被阻断，但具体层未定位到 |
| `output` | 输出阶段（L2+L5） | 在输出拦截点被阻断 |
| `tool_call` | 工具调用阶段（L4） | 在工具调用拦截点被阻断 |
| `memory_write` | 记忆写入阶段（L3） | 在记忆写入拦截点被阻断 |
| `memory_read` | 记忆读取阶段（L3） | 在记忆读取拦截点被阻断 |
| `agent_internal` | Agent 自身 | Agent 的内部安全逻辑拒绝了该请求（如 MockAgent 对危险请求的硬编码拒绝），非防御框架拦截 |
| `agent_error` | — | Agent 处理过程中抛出异常 |

> 绝大多数情况 `blocked_by` 直接返回层名（`source_governance` 等）。`input`/`output`/`tool_call`/`memory_write`/`memory_read` 仅在各层 `LayerCheckResult` 均显示 pass 但编排器汇总判定为 block 时才出现（罕见），此时表示拦截发生在阶段边界而非具体层内。

### 指标引擎 → MetricsSummary

- **基础指标**：DSR（防御成功率）、FPR（误报率）、FNR（漏报率）
- **混淆矩阵**：Accuracy、Precision、Recall、F1
- **分层统计**：各层拦截率贡献
- **攻击族 DSR**：12 族攻击的分别检出率
- **延迟统计**：avg、P50、P99 分位数

---

## 4. 如何连接到真实 Agent？

### Python Agent（同进程集成）

```python
import json
from orchestrator import DefenseOrchestrator
from defense_types import DefenseMode
from rule_engine import RuleEngine
from agent_adapter import DefenseWrapper

# 1. 加载规则引擎
with open('config/defense_rules.json', encoding='utf-8') as f:
    rules = [r for r in json.load(f)['rules'] if 'rule_id' in r]
engine = RuleEngine(rules)

# 2. 创建编排器
orch = DefenseOrchestrator(engine, mode=DefenseMode.BALANCED)

# 3. 包装你的 Agent
wrapper = DefenseWrapper(your_agent, orch)

# 使用：纯对话 Agent（覆盖 L1+L2+L5）
result = wrapper.run_with_defense(user_input="用户消息", source="user_input")

# 使用：带工具调用的 Agent（覆盖 L1+L2+L4+L5）
result = wrapper.run_with_tools(user_input="用户消息", source="user_input")

# 使用：单独拦截记忆操作
guard = wrapper.wrap_memory_write(content="记忆内容", source="user_input")
guard = wrapper.wrap_memory_read(query="查询", source="user_input")

# 处理结果
if not result.success:
    print(f"被 {result.blocked_by} 拦截: {result.blocked_reason}")
else:
    print(f"通过，Agent 回复: {result.original_response}")
```

### Agent 接口约定

你的 Agent 类需实现一个方法，返回 AgentResponse：

```python
class YourAgent:
    def receive_input(self, user_input: str, source: str) -> AgentResponse:
        # user_input: 用户输入的文本
        # source: 来源标识，如 "user_input" / "external_api"
        # 返回 AgentResponse(success=bool, content=str, action=str,
        #                     tool_name=str, tool_params=dict)
        ...
```

参考 `mock_agent.py` 的完整实现。

### 本地 Agent 接入 L3（记忆控制）和 L4（工具约束）

如果 Agent 只暴露单一对话接口，L3 和 L4 无法生效——因为记忆读写和工具调用发生在 Agent 内部，防御层看不到。本地部署拥有 Agent 源代码，需要在内部插入拦截调用。

**L3：代理 Agent 的记忆系统**

L3 采用代理模式——不让 Agent 直接操作记忆存储，而是通过 `MemoryControl` 读写。

第一步：实现 `MemoryBackend` 接口包装你现有的记忆后端（ChromaDB、FAISS、SQLite 等）：

```python
from layer3_memory_control import MemoryBackend

class YourMemoryBackend(MemoryBackend):
    """将你现有的记忆存储包装为 MemoryBackend 接口"""

    def __init__(self, your_existing_store):
        self._store = your_existing_store

    def write(self, entry_id, content, metadata):
        return self._store.insert(entry_id, content, metadata)

    def read(self, entry_id):
        return self._store.get(entry_id)

    def search(self, query, top_k=10):
        return self._store.similarity_search(query, k=top_k)

    def delete(self, entry_id):
        return self._store.remove(entry_id)

    def list_entries(self, status=None):
        return self._store.list_all(status)

    def update(self, entry_id, updates):
        return self._store.update_metadata(entry_id, updates)
```

第二步：在 Agent 代码中，把直接操作记忆的地方替换为经过 L3：

```python
from layer3_memory_control import MemoryControl

class YourAgent:
    def __init__(self):
        backend = YourMemoryBackend(self.memory_store)
        self.l3 = MemoryControl(backend, params={"default_ttl_hours": 24})

    # ==== 改前：Agent 直接写记忆 ====
    # def remember(self, content):
    #     self.memory_store.insert(content)

    # ==== 改后：经 L3 写入路径（4 项检查 + TTL 分配 + 冲突检测）====
    def remember(self, content, source="user_input"):
        allowed, action, entry = self.l3.write_entry(content, source)
        if not allowed:
            return f"记忆写入被拒绝: {action}"
        return f"已记忆: {content[:80]}"

    # ==== 改后：经 L3 读取路径（自动过滤 quarantined/archived/stale）====
    def recall(self, query):
        entries = self.l3.filter_read(query, top_k=5)
        return [e["content"] for e in entries]    # 只返回安全条目
```

**L4：在工具执行前插入检查**

L4 不替换任何组件——只在 Agent 的工具调度器中插入一行判断：

```python
from layer4_tool_constraint import ToolConstraint, ToolCall
from defense_types import DefenseContext
import json

class YourAgent:
    def __init__(self):
        self.l4 = ToolConstraint(params={
            "high_risk_actions": ["write_file", "delete_file",
                                  "execute_command", "run_script",
                                  "db_write", "send_email"],
        })

    # ==== 改前：Agent 直接执行工具 ====
    # def execute_tool(self, tool_name, params):
    #     return self.tool_registry[tool_name](**params)

    # ==== 改后：执行前经过 L4 检查 ====
    def execute_tool(self, tool_name, params, source="agent_core"):
        tc = ToolCall(tool_name=tool_name, params=params)
        ctx = DefenseContext(
            content=json.dumps({"tool": tool_name, "params": params},
                              ensure_ascii=False),
            source=source,
            content_type="tool_call",
        )
        l4_result = self.l4.evaluate(ctx, engine=None, tool_call=tc)
        if not l4_result.passed:
            return f"工具调用被 L4 拦截: {l4_result.action}"
        return self.tool_registry[tool_name](**params)
```

**简化方式：直接用 DefenseWrapper 的拦截方法**

上述手动调用等价于使用 DefenseWrapper 已内建的拦截点。Agent 内部代码只需将直接操作替换为 wrapper 方法：

```python
wrapper = DefenseWrapper(your_agent, orchestrator)

# 原来: self.memory_store.write(content)
# 改为:
guard = wrapper.wrap_memory_write(content, source)
if not guard.success: return guard.blocked_reason

# 原来: self.memory_store.search(query)
# 改为:
guard = wrapper.wrap_memory_read(query, source)
if not guard.success: return guard.blocked_reason

# 原来: self.tool_registry[name](**params)
# 改为:
guard = wrapper.wrap_tool_call(tool_name, params, source)
if not guard.success: return guard.blocked_reason
self.tool_registry[name](**params)
```

**一句话总结**：L3 和 L4 的接入就是在 Agent 代码中找两个位置各加一行调用——记忆操作前加 `wrap_memory_write/read`，工具执行前加 `wrap_tool_call`。不需要改 LLM 调用、对话管理或业务逻辑。

### 非 Python Agent（HTTP API 集成）

```bash
# 启动 API 服务
uvicorn server:app --host 0.0.0.0 --port 8100

# 提交检测请求
curl -X POST http://localhost:8100/api/defenses/test \
  -H "Content-Type: application/json" \
  -d '{"content": "用户输入或 Agent 输出", "source": "user_input"}'
```

返回完整的 DefenseTestResult JSON。此方式适用于 Node.js、Go 等非 Python Agent 系统。

**注意**：HTTP API 方式只能覆盖 L1+L2+L5（输入输出文本审查），L3 记忆控制和 L4 工具约束需要 Agent 进程内部的代码级拦截，无法通过外部 HTTP 调用实现。

### 重要约束

Agent 的所有对外交互路径必须经过 DefenseWrapper 的五个拦截点之一。如果 Agent 有绕过 wrapper 的"旁路"通道（如直接调用模型 API、直接操作文件系统而不经过工具接口），防御将失效。
