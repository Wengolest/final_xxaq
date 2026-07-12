# 启动指南

## 防御代理 — Defense Proxy (端口 8200)

通用方案：拦截所有 OpenAI 兼容的 Agent 流量，经过五层防御检测。

```cmd
cd C:\Users\LENOVO\defense_engine

# 安装依赖 (仅首次)
pip install fastapi uvicorn pydantic httpx

# 配置 API Key: 编辑 defense_proxy.py 第 57 行
# _HARDCODED_API_KEY = "sk-你的key"

# 启动代理
set DEFENSE_MODE=strict
uvicorn defense_proxy:app --host 0.0.0.0 --port 8200
```

启动后控制台会实时打印每层防御检测表格。

## 通用实验 (零 Agent 依赖)

```cmd
cd C:\Users\LENOVO\defense_engine
python experiment_via_proxy.py    # 42 样本 → HTTP → DSR/FPR 报告
```

## 后端管理面板 — Server (端口 8100)

```cmd
cd C:\Users\LENOVO\defense_engine

# 启动
uvicorn server:app --host 0.0.0.0 --port 8100
```

Swagger 文档: http://localhost:8100/docs

## 前端 — Web Dashboard (React)

```bash
cd C:\Users\LENOVO\web

# 安装依赖 (仅首次)
pnpm install

# 默认 Mock 模式 (无需后端)
pnpm dev

# 真实 API 模式: 编辑 .env, 设置 VITE_USE_MOCK=false
```

浏览器访问: http://localhost:5173

## 其他常用命令

```cmd
# 标准化实验 — 进程内 MockAgent (42样本 × 3模式)
python experiment.py

# 端到端演示
python demo_end_to_end.py

# 单元测试 (251项)
python run_tests.py

# 快速单样本测试
python ATEST.py
```

## Agent 接入方式

任意 OpenAI 兼容 Agent (LangChain / smolagents / CrewAI / 直接 SDK)，改一行代码：

```python
client = OpenAI(base_url="http://localhost:8200/v1", api_key="no-needed")
```

所有请求自动经过五层防御，无需修改 Agent 逻辑。
