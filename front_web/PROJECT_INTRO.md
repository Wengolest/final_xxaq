# Web Dashboard — LLM Agent 安全评估平台前端

基于 React 19 + TypeScript + Vite 构建的 LLM Agent 安全评估可视化平台，提供攻击配置、防御管理、实验执行与结果分析的一站式 Web 界面。

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | React 19 |
| 语言 | TypeScript 6 |
| 构建 | Vite 8 |
| UI 库 | Ant Design 6 |
| 图表 | ECharts 5 |
| 路由 | React Router 7 |
| 状态管理 | Zustand |
| 包管理 | pnpm |

## 功能页面

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | Dashboard | 系统总览、健康状态、关键指标卡片 |
| `/targets` | TargetManagement | Agent 目标配置与管理 |
| `/attacks` | AttackConfig | 攻击样本配置（9 族 45 条） |
| `/defense` | DefenseConfig | 五层防御规则配置 |
| `/experiments` | ExperimentCenter | 实验执行与进度监控 |
| `/results` | ResultAnalysis | 结果分析：热力图、趋势图、DSR/FPR、判决分布 |
| `/variants` | VariantAnalysis | 攻击变体深度分析 |
| `/audit` | AuditLog | 审计日志查看 |


## 快速启动

```bash
cd web
pnpm install
pnpm dev          # 启动开发服务器 → http://localhost:5173
pnpm build        # 生产构建 → dist/
```

## 项目结构

```
web/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── .env                        # VITE_USE_MOCK 开关
└── src/
    ├── main.tsx                # 入口
    ├── App.tsx                 # 路由配置
    ├── index.css               # 全局样式
    ├── api/                    # API 层（类型、客户端、Mock 数据）
    ├── components/             # 通用组件（布局、指标卡片、攻击标签）
    ├── pages/                  # 8 个功能页面
    ├── store/                  # Zustand 状态管理
    └── utils/                  # 工具函数（颜色映射、格式化）
```


