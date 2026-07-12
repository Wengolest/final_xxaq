# LLM Agent 安全评测平台 — 前端

面向大语言模型智能体（LLM Agent）的自动化安全评测系统前端。以 React + TypeScript + Ant Design + ECharts 技术栈构建，覆盖"目标管理 → 攻击配置 → 防御配置 → 实验编排 → 结果分析 → 审计回溯"完整工作流，支持前端独立运行（Mock 数据驱动）以及与 Python 后端联调两种模式。

## 技术栈

| 类别 | 选型 | 版本 |
|------|------|------|
| 框架 | React | ^19.2 |
| 语言 | TypeScript | ~6.0 |
| UI 组件 | Ant Design | ^6.3 |
| 图表 | ECharts + echarts-for-react | ^6.0 / ^3.0 |
| 路由 | React Router | ^7.14 |
| 状态管理 | Zustand | ^5.0 |
| HTTP | Axios | ^1.15 |
| 构建 | Vite | ^8.0 |

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5173）
npm run dev

# 生产构建
npm run build

# 预览生产构建
npm run preview
```

开发模式下，前端使用内置 Mock 数据独立运行，无需后端。Mock 数据位于 `src/api/mock.ts`，涵盖 4 个 Agent 目标、12 个攻击族、5 个攻击样本、5 层防御配置、4 条实验记录及对应的评估结果和事件时间线。

## 项目结构

```
web/
├── index.html
├── package.json
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
├── vite.config.ts
└── src/
    ├── main.tsx                    # 入口
    ├── App.tsx                     # 根组件（路由 + 布局 + 代码分割）
    │
    ├── api/                        # API 层
    │   ├── client.ts               # Axios 实例（预留拦截器）
    │   ├── types.ts                # 全部 DTO 接口定义
    │   ├── mock.ts                 # Mock 数据源
    │   ├── target.ts               # Agent 目标管理 API
    │   ├── attack.ts               # 攻击模块 API
    │   ├── defense.ts              # 防御模块 API
    │   ├── experiment.ts           # 实验编排 API
    │   └── evaluation.ts           # 评估结果 API
    │
    ├── store/                      # 状态管理（Zustand）
    │   ├── targetStore.ts          # 目标管理状态
    │   ├── experimentStore.ts      # 实验运行状态
    │   └── uiStore.ts             # 全局 UI 状态
    │
    ├── pages/                      # 页面组件（按路由懒加载）
    │   ├── Dashboard/              # 仪表盘
    │   ├── TargetManagement/       # Agent 目标管理
    │   ├── AttackConfig/           # 攻击配置
    │   ├── DefenseConfig/          # 防御配置
    │   ├── ExperimentCenter/       # 实验编排中心
    │   │   └── ExperimentDetail/   #   实验详情
    │   ├── ResultAnalysis/         # 结果分析
    │   ├── VariantAnalysis/        # 攻击变体分析
    │   └── AuditLog/              # 审计日志
    │
    ├── components/                 # 共享组件
    │   ├── Layout/                 # 主布局（侧栏 + 内容区）
    │   └── MetricCard/             # 指标卡片
    │
    └── utils/                      # 工具函数
        ├── constants.ts            # 枚举定义（攻击族/防御层/风险等级等）
        ├── formatters.ts           # 数值/日期格式化
        └── colorMap.ts            # 配色映射
```

## 页面路由

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | Dashboard | 项目健康度总览（目标规模/攻击族覆盖/实验进度/高威胁发现） |
| `/targets` | TargetManagement | Agent 目标注册、编辑、健康检查、能力标签管理 |
| `/attacks` | AttackConfig | 攻击族气泡图 + 分类卡片 + 样本管理 + 变体生成 |
| `/defenses` | DefenseConfig | 五层防御 Steps 可视化配置 + 逐层规则管理 |
| `/experiments` | ExperimentCenter | 实验创建、启动/停止、历史记录 |
| `/experiments/:runId` | ExperimentDetail | 单次实验详情（进度圆环 + 事件时间线） |
| `/results/:runId` | ResultAnalysis | 多因子评估结果（指标卡片 + ASR/DSR 对比图 + 趋势图 + 明细表） |
| `/variants` | VariantAnalysis | 攻击变体横向对比（变体策略 × 目标 × 防御层） |
| `/audit` | AuditLog | 全局事件汇总 + 关键词搜索 + 审计时间线 |

## API 设计

前后端通过 RESTful API 以 JSON 格式通信，共 5 组 25 条端点。完整的接口契约见 LaTeX 文档 §2.5 中"前后端接口契约与数据模型"一节。

| API 组 | 路径前缀 | 端点数 |
|--------|---------|--------|
| 目标管理 | `/api/targets` | 6 |
| 攻击管理 | `/api/attacks` | 5 |
| 防御管理 | `/api/defenses` | 4 |
| 实验编排 | `/api/experiments` | 6 |
| 评估结果 | `/api/evaluations` | 4 |

### 从 Mock 切换到真实后端

每个 API 模块（如 `src/api/target.ts`）采用相同的结构：

```typescript
// 当前：Mock 调用
export async function getTargets(): Promise<TargetAgent[]> {
  await delay();
  return [...mockTargets];
}

// 切换为：真实 HTTP 请求（仅需替换函数体）
// import client from './client';
// export const getTargets = () => client.get('/targets');
```

页面组件不感知底层实现，仅依赖函数签名和 `api/types.ts` 中的接口定义。切换后端时无需修改任何页面代码。

## 状态管理

三个 Zustand Store 各自独立，不相互依赖：

- **targetStore** — Agent 目标列表、加载状态、健康检查结果映射、CRUD 操作
- **experimentStore** — 实验列表、当前实验详情、创建/启动/停止操作
- **uiStore** — 侧栏折叠状态（预留主题切换等全局配置）

## 核心数据结构

| 接口 | 关键字段 | 使用页面 |
|------|---------|---------|
| `TargetAgent` | id, name, base_url, capabilities, status, rag_config, memory_config | 目标管理、实验创建 |
| `AttackFamilyNode` | family, category, risk_level, asr, impact, stealth, risk_score | 攻击配置（气泡图/卡片/标签） |
| `DefenseLayerConfig` | layer, enabled, rules[], params | 防御配置（Steps + 规则表） |
| `Experiment` | run_id, target_ids[], attack_families[], defense_layers[], status, progress | 实验编排、仪表盘 |
| `EvaluationSummary` | asr, dsr, h_cum, risk_score, by_family{} | 结果分析、仪表盘 |
| `AttackVariant` | variant_id, case_id, variant_strategy, success, score | 变体分析 |

## 开发约定

- **TypeScript 严格模式**：`erasableSyntaxOnly: false`（允许 enum）
- **代码分割**：所有页面通过 `React.lazy` + `Suspense` 按路由懒加载
- **枚举集中管理**：攻击族、防御层、风险等级等枚举统一定义在 `utils/constants.ts`
- **配色统一**：攻击族/风险等级/实验状态的配色映射集中在 `utils/colorMap.ts`
- **ESLint**：`npm run lint` 检查代码风格

## 与后端协作要点

1. 前后端通过 `api/types.ts` 维护类型契约，任何字段变更需同步更新
2. Mock 数据应保持与真实 API 响应格式一致，确保切换时无差异
3. 新功能开发流程：定义类型 → 添加 Mock → 实现页面 → 后端联调 → 移除 Mock
