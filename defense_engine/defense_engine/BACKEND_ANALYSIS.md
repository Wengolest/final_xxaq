# Defense Engine 后端分析报告

> 生成日期：2026-05-27 | 用途：论文准备材料

---

## 零、架构亮点：defense_proxy — OpenAI 兼容反向代理

`defense_proxy.py`（637 行）是本项目**最核心的架构贡献**。它是一个 OpenAI 兼容的反向代理，在 Agent 与 LLM 后端之间透明插入五层防御检测。

### 设计理念

```
Agent (Smolagents / LangChain / OpenAI SDK / ...)
  │  HTTP POST /v1/chat/completions
  │  base_url = "http://localhost:8200/v1"
  ▼
┌─────────────────────────────────────────┐
│         Defense Proxy (:8200)           │
│                                         │
│  输入侧: 提取 messages                   │
│    → L1 源头治理 + L2 模型交互           │
│                                         │
│  转发到后端 LLM (DeepSeek)               │
│                                         │
│  输出侧: 提取 content + tool_calls       │
│    → L4 工具约束 + L2 + L5 决策监督      │
│                                         │
│  返回: 放行(带 defense 元数据) / 拦截(400) │
└─────────────────────────────────────────┘
  │
  ▼
LLM Backend (DeepSeek API)
```

### 核心优势

| 特性 | 说明 |
|---|---|
| **零代码接入** | Agent 仅需改 `base_url`，无需修改任何 Agent 代码 |
| **通用兼容** | 任意 OpenAI 兼容框架均可接入（Smolagents, LangChain, AutoGen, CrewAI 等） |
| **透明拦截** | Agent 完全无感知防御层存在 |
| **双流式支持** | 同时支持流式和非流式响应，流式模式下先缓冲再检测后放行 |
| **丰富元数据** | 响应附加 `defense` 字段，逐层返回 risk_score / action / flags / matched_rules |
| **标准错误格式** | 拦截时返回 `error.type="content_filter"`，Agent 可按标准方式处理 |
| **控制台可视化** | 实时打印逐层检测表格（Layer / Action / Risk / Trust / Rules / Flags） |

### 覆盖范围

| 拦截点 | 覆盖层 | 检测内容 |
|---|---|---|
| 输入侧 (messages) | L1 + L2 | 来源、零宽字符、编码混淆、角色混淆、Jailbreak/DAN、PII |
| 输出侧 (text content) | L2 + L5 | 敏感内容泄露、异常模式检测 |
| 输出侧 (tool_calls) | L4 | 工具白名单、权限分级、危险命令、敏感路径、速率限制 |

### 代理模式的固有架构局限

以下是代理模式**结构上无法覆盖**的盲区，不是工程实现不足，而是代理位置决定的：

**1. L3 记忆控制无法覆盖**

代理只能看到 API 请求/响应，无法感知 Agent 进程内部的记忆读写操作。Smolagents 等框架的记忆存储在 Agent 进程内存中，对代理完全不可见。这意味着：
- 记忆投毒攻击（长期潜伏在记忆中）无法被代理检测
- 记忆冲突检测（新旧知识矛盾）无法执行
- L3 仅在 Agent 显式接入 `DefenseWrapper` 或使用持久化 MemoryBackend 时才有意义

**2. 流式响应必须全量缓冲**

代理需要在完整响应到达后才能执行输出侧防御检测。流式模式下：
- 缓冲区内存占用与输出长度成正比
- 用户感知延迟增加（缓冲时间 + 检测时间）
- 无法"边生成边检测边放行"——一旦开始发送 chunk 就无法撤回

**3. 仅覆盖 `/v1/chat/completions` 端点**

OpenAI API 的其他端点（`/v1/embeddings`、`/v1/images/generations`、`/v1/audio` 等）不受保护。如果 Agent 使用多模态能力（图片理解、语音），这些通道的攻击面不在防御范围内。

**4. 无 Agent 身份感知**

代理可看到请求头中的 API Key，但当前不利用它做：
- 按 Agent/租户的差异化防御策略
- 按用户的速率限制隔离
- 按身份的审计追踪

**5. 单一后端 LLM 硬编码**

当前仅支持 DeepSeek API。切换到 OpenAI / Claude / 本地模型需要修改源码。生产环境中可能需要多后端路由（不同 Agent 用不同模型）。

---

## 一、架构层面

### 1.1 无持久化存储

所有数据均存在于 Python 内存中，服务重启即全部丢失：

| 数据 | 存储方式 | 影响 |
|---|---|---|
| 实验数据 `_experiments_store` | `dict` | 所有历史实验结果不可追溯 |
| 审计日志 `_audit_log` | `list` | 审计记录无持久化 |
| 记忆后端 `SimulatedMemoryBackend` | `dict` | Agent 记忆无持久化 |
| 速率限制计数器 | `dict` | 重启后速率限制重置 |
| 统计数据 | 模块级变量 | Metrics 历史无法回溯 |

无数据库、无文件存储、无导出功能。

### 1.2 L3 记忆控制为模拟实现

- `MemoryBackend` 为抽象类，仅有的 `SimulatedMemoryBackend` 实现基于 Python dict
- 不具备向量检索能力，文档明确标注需替换为真实向量数据库
- `write_entry()` 存在疑似逻辑反转：`"untrusted_source" not in risk_flags` 时状态设为 `"active"`
- 不检查 `max_memory_entries` 上限

### 1.3 SemanticScorer 为占位符

- `scoring.py` 中整个 `SemanticScorer` 抽象类仅为文档预留
- `PassThroughScorer` 始终返回 `severity="log"` + `label="safe"`
- 权重 `semantic_block=0.40` / `semantic_warn=0.15` 已定义但从未被触发
- 无任何 ML 模型集成

### 1.4 agent_adapter 仅对接 MockAgent

- `DefenseWrapper`（`agent_adapter.py`）的 5 个拦截点设计完善，但仅与 `MockAgent` 对接
- 接入真实 Agent 需要额外编写适配器
- 相比之下 `defense_proxy.py` 是更通用的接入方案（无需适配器），但只能覆盖 API 层面的 4 层（缺 L3）

---

## 二、检测能力层面

### 2.1 L1 编码混淆检测盲区

| 问题 | 详情 |
|---|---|
| Base64 检测仅匹配英文关键词 | 关键词集 `system\|prompt\|instruction\|ignore\|bypass\|override`，中文攻击文本可绕过 |
| 重复检测阈值过高 | 正则 `(.{40,})\1{2,}` 要求 ≥40 字符且精确重复 3 次，无法检测变体模式（如模板注入） |
| 来源检测宽松 | 未知/空来源仅产生 `warn`（non-blocking），BALANCED/PERMISSIVE 模式下不阻断 |

### 2.2 L2 Token 估算粗糙

- 全局使用 `len(content) // 2` 估算 token 数
- 中文文本严重偏差：中文字符约 1.5-2 token/字，英文约 0.3-0.5 token/字
- 上下文限制固定 16000，不考虑下游模型差异（GPT-4 / Claude / DeepSeek tokenizer 各不相同）

### 2.3 L3 冲突检测仅支持中文

- 仅 4 对中文关键词极性对比：安全↔危险、正常↔异常、允许↔禁止、合规↔违规
- 无英文否定结构检测（"not safe"、"not recommend" 等）
- 无向量相似度比较，无跨语言语义理解

### 2.4 L4 权限与速率限制缺陷

- 速率限制仅按工具名做滑动窗口计数，无 token bucket / 突发容许
- 无按用户/Agent 隔离（多 Agent 共享工具名会互相干扰）
- 权限等级 `network`(1) 和 `write`(2) 从不触发任何警告
- 审计日志无上限，可无限增长

### 2.5 L5 冷启动盲区

- 异常检测需 ≥10 条历史决策才启用新 flag 检测
- 高风险比率检测需 ≥5 条历史决策
- 系统启动后的前 10 次评估完全无异常检测覆盖
- flag 字符串含动态 Unicode 码点，导致相同类型的零宽字符检测被误判为"新攻击类型"
- 熔断时间硬编码 60 秒，不可按部署场景配置

### 2.6 拒绝检测为简单字符串匹配

- `_check_refusal()` 仅用 16 条中英文字符串做 `lower() in text` 子串匹配
- 漏检风险：LLM 用委婉措辞拒绝时无法识别（如 "Perhaps you should reconsider..."）
- 误检风险：正常回复含 "I cannot" 等短语时可能误判
- 无 LLM-as-judge 或分类器做语义判断

---

## 三、工程质量层面

### 3.1 硬编码问题

| 位置 | 硬编码内容 |
|---|---|
| `defense_proxy.py:57` | DeepSeek API Key 明文 |
| `server.py:133-209` | 28 条实验样本（与另外 2 个文件重复） |
| `server.py:258` | Proxy URL `http://localhost:8200` |
| `server.py` | 模型名 `deepseek-chat` |
| 5 个文件 | 五层名称列表 `["source_governance", ...]` 逐字重复 |
| `orchestrator.py:59-79` | 各层参数硬编码为 dict |
| `layer5_decision_supervision.py` | 熔断时间 60s |

### 3.2 代码重复

- `_checks_to_flags()` / `_rule_matches_to_flags()` / `_summarize()` 在 L1-L5 五个文件中几乎完全相同
- `_context_snippet()` 在 L1、L2、L4 中重复实现
- `_find_blocking_layer()` 在 `agent_adapter.py` 和 `defense_proxy.py` 中重复
- 实验样本 28 条在 `server.py`、`experiment.py`、`experiment_via_proxy.py` 三处重复

### 3.3 RuleEngine 使用 eval()

- `_eval_condition()` 调用 Python `eval()` 执行规则条件
- 虽传入了 `{"__builtins__": {}}`，仍存在代码注入风险
- 无效正则静默设为 `None`，无日志或警告

### 3.4 无认证授权

- 所有 API 端点完全开放
- 规则 CRUD、实验执行、配置修改均无需身份验证

### 3.5 实验模块设计问题

- 规则模式与 Proxy 模式代码路径完全分离，大量重复逻辑
- Proxy 实验运行中无法取消（后台线程无停止机制）
- 实验失败无重试（标记 error 后跳过）
- 测试目标选择字段为占位符，选任何值不影响实际行为
- 实验对比 API 已实现但前端无入口

### 3.6 日志与时间戳不一致

- `server.py` 使用 `print()`，`defense_proxy.py` 使用 `logging`，Layer 文件无任何日志
- 时间戳有的用 `datetime.now(timezone.utc)`，有的用 `time.time()`

---

## 四、评估指标局限性

### 4.1 规则模式指标为近似值

| 指标 | 规则模式 | 说明 |
|---|---|---|
| DSR | 真实 | 规则引擎拦截率 |
| ASR | **近似** `1 - DSR` | 假设未拦截 = 攻击成功 |
| refusal_rate | **硬编码 0** | 无 LLM 参与 |
| task_drift_rate | **硬编码 0** | 两种模式均如此 |
| prp / btr | **硬编码 0** | 需真实 Agent 记忆+任务观测 |
| H_cum | **近似** `DSR × 0.5` | 非实际测量值 |

### 4.2 Proxy 模式也无法覆盖所有指标

- `task_drift_rate`、`prp`、`btr` 在两种模式下都硬编码为 0
- 这些指标需要：真实 Agent 任务执行 + 任务完成度评估 + 持久化记忆观测
- 当前实验框架不具备以上条件

### 4.3 无单样本级别回复审查

- Proxy 模式结果中 `llm_reply` 被截断到 200 字符
- 前端不展示单样本 LLM 回复
- 无法人工复核拒答/失陷分类是否正确

---

## 五、论文写作指导

### 论文中可强调的优势

1. **透明代理架构**：`defense_proxy` 实现 OpenAI 兼容反向代理，任意 Agent 仅需修改 `base_url` 即可零代码接入五层防御，无需修改 Agent 内部逻辑
2. **五层纵深防御**：L1→L5 串联执行，信任度逐层衰减，支持 STRICT/BALANCED/PERMISSIVE 三种模式灵活切换
3. **双模式实验评估**：规则模式（秒级自检，无 API 消耗）+ Proxy 模式（真实 LLM 攻击测试，真实 ASR）
4. **输入输出双向检测**：输入侧 L1+L2，输出侧 L2+L4+L5，覆盖 prompt 注入和工具滥用两个主要攻击面

### 建议写入论文的局限性

1. **代理模式的固有盲区**：反向代理无法感知 Agent 内部记忆操作，L3 记忆控制在代理模式下不可用；流式响应需全量缓冲后检测，引入额外延迟
2. **检测粒度有限**：编码混淆检测以英文关键词为主，对非英文攻击文本覆盖不足；冲突检测仅支持中文关键词极性对，缺乏跨语言语义理解能力
3. **语义评分模块未完成**：SemanticScorer 尚未接入 ML 模型，语义维度的风险评估完全缺失
4. **记忆控制为原型级**：L3 使用模拟记忆后端，不具备向量检索和语义冲突检测能力
5. **冷启动防护不足**：L5 异常检测在系统运行初期存在盲区
6. **无持久化能力**：所有实验数据、审计记录均为内存存储，无法长期追踪
7. **仅支持单一 LLM 提供商**：Proxy 硬编码 DeepSeek API
8. **实验评估指标不完整**：task_drift_rate、prp、btr 始终为 0，缺乏真实 Agent 任务完成度观测

### 建议在论文中规避的内容

- API Key 硬编码、`eval()` 使用等工程安全问题
- 代码重复、copy-paste boilerplate
- 日志系统不一致
- MockAgent 非真实 LLM 的模拟性质（可表述为"基于规则的系统测试"）
- agent_adapter 仅对接 MockAgent（可强调 proxy 是推荐的通用接入方式）

### 未来工作方向

- **L3 代理集成**：通过 Agent 框架的 memory callback/middleware 机制将记忆操作暴露给代理
- **流式早期截断**：实现 token 级别的增量检测，支持在流式传输中实时拦截
- **多端点覆盖**：扩展代理至 `/v1/embeddings` 等多模态端点
- 接入 Llama Guard / 训练专用分类模型实现 SemanticScorer
- 将 SimulatedMemoryBackend 替换为向量数据库（Milvus/Pinecone/Chroma）
- 实现多 LLM 提供商适配层（OpenAI / Claude / 本地模型）
- 增加实验持久化（SQLite/PostgreSQL）和对比分析 UI
- Token 估算替换为模型原生 tokenizer（tiktoken / transformers）
- 拒绝检测升级为 LLM-as-judge 语义判断
- 实现真实 Agent 任务执行观测（task_drift_rate / prp / btr）
