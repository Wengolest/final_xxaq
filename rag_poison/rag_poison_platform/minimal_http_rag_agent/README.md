# minimal_http_rag_agent

轻量 HTTP RAG 服务（TF-IDF + DeepSeek），用于平台端到端投毒验证。

## 启动

```powershell
cd D:\AI\rag_poison_exp\rag_poison_platform\minimal_http_rag_agent
.\run_server.ps1
```

服务地址：`http://127.0.0.1:18100`

## API

- `GET /health`
- `POST /reset`
- `POST /ingest` — `{doc_id, text, source: clean|poison, metadata}`
- `POST /query` — `{question, top_k}`

## 依赖

独立 `.venv`，不安装进 `rag_poison_platform` 主环境。

LLM 配置读取上级 `rag_poison_platform\.env` 中的 `DEEPSEEK_*` 变量。
