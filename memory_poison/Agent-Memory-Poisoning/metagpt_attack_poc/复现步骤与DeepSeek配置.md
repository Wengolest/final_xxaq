# 记忆投毒复现步骤 + 全量使用 DeepSeek 配置说明

本文档面向零基础复现本仓库的**记忆投毒攻击**，并把所有需要调用大模型的地方改为使用 **DeepSeek**（不再使用 OpenAI）。

---

## 一、环境准备

### 1.1 系统要求

- **Python**：3.9 或 3.10（建议 3.10，不要用 3.12+）
- **系统**：Windows / macOS / Linux 均可

检查 Python 版本：

```bash
python --version
# 或
python3 --version
```

### 1.2 克隆/进入项目目录

项目根目录应为 `Agent-Memory-Poisoning`（即包含 `metagpt`、`metagpt_attack_poc`、`config` 的目录）。在终端中进入该目录：

```bash
cd C:\Users\Lenovo\Desktop\memory_attack\Agent-Memory-Poisoning
```

后续所有命令都默认在该根目录下执行。

### 1.3 创建虚拟环境（推荐）

```bash
python -m venv venv
# Windows 激活:
venv\Scripts\activate
# macOS/Linux 激活:
# source venv/bin/activate
```

### 1.4 安装依赖

**重要**：必须用**本仓库**的 metagpt（可编辑安装），不要用 PyPI 的 `metagpt`。若之前装过 PyPI 版，先卸载再按下面顺序安装。

在项目根目录 `Agent-Memory-Poisoning` 下执行：

```bash
pip uninstall metagpt -y
pip install -e .
pip install -r requirements.txt
pip install -r metagpt_attack_poc/requirements.txt
```

若只装 POC 的 `requirements.txt`，可能缺少 `tree_sitter_python`、`sparkai` 等，导致导入报错。已对 `metagpt.provider` 做可选导入处理，未安装讯飞/千帆/通义等 SDK 时不影响使用 DeepSeek；但 `tree_sitter_python` 等仍须从主项目 `requirements.txt` 安装。

如需 RAG/向量检索（实验 4 的 FAISS），可安装 RAG 额外依赖：

```bash
pip install -e ".[rag]"
```

---

## 二、把 OpenAI 全部改为 DeepSeek

所有“调大模型”的地方都通过 **全局配置文件** 和 **环境变量** 决定，无需改实验脚本代码。按下面做即可全部走 DeepSeek。

### 2.1 获取 DeepSeek API Key

1. 打开 [DeepSeek 开放平台](https://platform.deepseek.com/) 并登录。
2. 在控制台里创建或复制 **API Key**（形如 `sk-...`）。

### 2.2 配置方式一：改配置文件（推荐）

编辑项目根目录下的 **`config/config2.yaml`**（不是 `metagpt_attack_poc` 里的文件）。

把 `llm` 和（如需要）`embedding` 改成下面这样，即使用 DeepSeek 的 OpenAI 兼容接口：

```yaml
llm:
  api_type: "openai"
  model: "deepseek-chat"
  base_url: "https://api.deepseek.com/v1"
  api_key: "${OPENAI_API_KEY}"

embedding:
  api_type: "openai"
  base_url: "https://api.deepseek.com/v1"
  api_key: "${OPENAI_API_KEY}"
  model: ""
  dimensions: 1536
```

说明：

- `api_type: "openai"` 保持不变即可，DeepSeek 兼容 OpenAI 接口，只需改 `base_url` 和 `model`。
- `api_key` 用环境变量 `OPENAI_API_KEY`，在下一步里把该变量设为你的 **DeepSeek API Key**。

若要用 **深度推理模型**，可把 `model` 改为：

```yaml
model: "deepseek-reasoner"
```

### 2.3 配置方式二：环境变量

在项目**根目录** `Agent-Memory-Poisoning` 下创建或编辑 **`.env`** 文件（与 `config`、`metagpt` 同级），内容示例：

```env
OPENAI_API_KEY=sk-你的DeepSeek的API密钥
```

若希望用环境变量覆盖 `base_url` 和 `model`（部分逻辑会读环境变量），可增加：

```env
OPENAI_API_KEY=sk-你的DeepSeek的API密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

**注意**：  
- 配置文件里的 `base_url` 和 `model` 已按上面 2.2 改好的话，通常不需要再设 `OPENAI_BASE_URL` / `LLM_MODEL`。  
- **`.env` 必须放在项目根目录 `Agent-Memory-Poisoning` 下**（与 `config`、`metagpt` 同级），这样 `config2.py` 里 `_load_env_file()` 才能从 `METAGPT_ROOT/.env` 读到。可参考根目录下的 `.env.example`，复制为 `.env` 后填入 DeepSeek API Key。

### 2.4 小结：哪里算“改成 DeepSeek”

- **改动的只有**：`config/config2.yaml` 的 `llm`（以及可选的 `embedding`）+ 环境变量 `OPENAI_API_KEY`（或 `.env`）。
- **不需要改**：  
  - 各个实验脚本（`exp1_*.py`, `exp2_*.py`, `exp3_*.py`, `exp4_*.py`）  
  - `metagpt` 里调用 LLM 的代码  

只要配置指向 DeepSeek，所有原先“调 OpenAI”的请求都会发到 DeepSeek。

---

## 三、记忆投毒实验复现步骤

### 实验概览

| 实验 | 脚本 | 目的 |
|------|------|------|
| 实验 1 | exp1_schema_spoof.py | Schema 欺骗：README 中伪造 ReAct 痕迹，看智能体是否采纳危险命令 |
| 实验 2 | exp2_judge_jack.py | Judge 劫持：用假“成功”输出欺骗验证逻辑 |
| 实验 3 | exp3_memory_graft.py | 记忆嫁接：向经验池注入毒数据，观察检索是否返回毒记忆 |
| 实验 4 | exp4_rag_vector_drift.py | RAG 向量漂移：构建带毒 RAG 索引，测 PRR（毒检索率） |

以下均在 **项目根目录** `Agent-Memory-Poisoning` 下执行（且已按第二节配好 DeepSeek）。

### 3.1 实验 1：Schema 欺骗（需调用 LLM）

```bash
python metagpt_attack_poc/experiments/exp1_schema_spoof.py
```

- **会做什么**：把 `metagpt_attack_poc/test_repo_schema_spoof` 复制到 `workspace/test_repo_schema_spoof`，然后启动 DataInterpreter，让它根据 README 做“部署”；README 里含有伪造的 Thought/Action/Observation，诱导执行危险命令。
- **预期**：若攻击成功，输出中会出现如 `curl ... | bash`、`deploy --skip-tests` 等危险模式。
- **耗时**：约 30–60 秒（会调 DeepSeek）。

### 3.2 实验 2：Judge 劫持（需调用 LLM）

```bash
python metagpt_attack_poc/experiments/exp2_judge_jack.py
```

- **会做什么**：用假成功脚本（只打印成功标记、不做事）让智能体执行并验证“是否成功”。
- **预期**：智能体被假输出欺骗，认为任务成功。
- **耗时**：约 30–60 秒（会调 DeepSeek）。

### 3.3 实验 3：记忆嫁接（需 Chroma/向量，可选 LLM）

```bash
python metagpt_attack_poc/experiments/exp3_memory_graft.py
```

- **会做什么**：向经验池注入毒经验，再用语义检索查询，看是否检索到毒记忆。
- **依赖**：`config2.yaml` 里 `exp_pool` 会设为 Chroma 等；若需向量检索，需配好 `embedding`（上面 2.2 已含）。
- **耗时**：约 10–20 秒（若只做内存/检索，可不怎么调 LLM）。

### 3.4 实验 4：RAG 向量漂移（可选 LLM）

```bash
python metagpt_attack_poc/experiments/exp4_rag_vector_drift.py
```

- **会做什么**：用 `payloads/experience_seeds.json` 构建 RAG 索引（BM25 必选；若配了 embedding 则还有 FAISS），并测毒检索率 PRR。
- **无 embedding**：仅 BM25，仍可复现“毒条目被检索”的效应。
- **有 embedding**：在 2.2 中已配好 `embedding` 后，会启用 FAISS 向量检索。
- **耗时**：约 10–30 秒。

---

## 四、常见问题

### 4.0 报错 “metagpt 0.7.4 与 aiohttp/anthropic/openai/... 版本不兼容”

这是本机装的是 **PyPI 上的 metagpt 0.7.4**，它的依赖版本和当前 `requirements.txt` 里不一致导致的。复现应用**本仓库**的代码，不要用 PyPI 的包。

在项目根目录执行：

```bash
pip uninstall metagpt -y
pip install -e .
```

再执行 `pip install -r requirements.txt`（若之前已装过，可跳过）。之后用 `python -c "import metagpt; print(metagpt.__file__)"` 检查，路径应指向你本地的 `Agent-Memory-Poisoning` 目录，而不是 site-packages 里的 0.7.4。

---

### 4.1 报错 “Please set your API key in config2.yaml”

- 确保在 **项目根目录** 的 `config/config2.yaml` 里，`llm.api_key` 为 `"${OPENAI_API_KEY}"`。
- 在**同一根目录**下存在 `.env`，且其中有 `OPENAI_API_KEY=sk-你的DeepSeek密钥`；或在当前 shell 中 `export OPENAI_API_KEY=sk-...`（Windows 用 `set OPENAI_API_KEY=sk-...`）。

### 4.2 请求还是发到 OpenAI 或报错 404

- 检查 `config/config2.yaml` 里 `llm.base_url` 是否为 `https://api.deepseek.com/v1`，`llm.model` 是否为 `deepseek-chat`（或 `deepseek-reasoner`）。
- 若用 `.env` 覆盖，确认没有把 `OPENAI_BASE_URL` 设成 OpenAI 的地址。

### 4.3 实验 1/2 报错或卡住

- 确认 DeepSeek 的 key 有效、网络可访问 `api.deepseek.com`。
- 若超时，可在 `config/config2.yaml` 里为 `llm` 增加 `timeout: 120`（或更大）。

### 4.4 实验 3/4 的 embedding/FAISS 相关报错

- 若暂时不用向量检索，可不在 `config2.yaml` 里配 `embedding`，或 `embedding.api_key` 留空；实验 4 会退化为仅 BM25。
- 若要用 FAISS：保持 2.2 的 `embedding` 配置，且 `embedding.api_key` 与 DeepSeek 的 key 一致（DeepSeek 若未提供官方 embedding 接口，可先注释掉 FAISS 或改用其他兼容 OpenAI embedding 的服务并相应改 `base_url`）。

---

## 五、结果文件位置

- 实验 1–4 的日志/结果一般在 **`metagpt_attack_poc/results/`** 下，如：
  - `exp1_schema_spoof_*.txt`
  - `exp2_judgejack_*.txt`
  - `exp3_memory_graft_*.txt`
  - `exp4_rag_vector_drift_*.json`
- 实验 4 的 RAG 索引会持久化在 **`metagpt_attack_poc/results/rag_poison_store/`**。

按上述步骤即可在**全部使用 DeepSeek** 的前提下复现记忆投毒相关实验；无需改任何调用 OpenAI 的代码，只改配置即可。
