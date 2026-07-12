# 前端清理报告 — Web Dashboard (React 19 + Vite)

> 项目路径：`C:\Users\LENOVO\web` | 2026-06-29 | 纯搜查，未修改任何文件

---

## 一、注释性 / 文档性文件（建议删除）

| # | 文件 | 说明 |
|---|------|------|
| 1 | `README.md` | 160 行中文项目文档（技术栈、路由表、API 说明、页面描述、开发规范） |
| 2 | `.claude\settings.local.json` | Claude Code 本地配置（工具权限白名单） |

---

## 二、构建产物（建议删除）

| # | 路径 | 说明 |
|---|------|------|
| 3 | `dist\` 整个目录 | Vite 生产构建输出（34 个 JS chunk + 1 CSS + HTML） |

---

## 三、环境配置文件

| # | 文件 | 内容 | 风险 |
|---|------|------|------|
| 4 | `.env` | 仅一行 `VITE_USE_MOCK=false` | **无风险**（无 Key / 凭据） |

> `vite.config.ts` 第 10 行含 `target: 'http://localhost:8100'`，仅本地开发代理，无风险。

---

## 四、Mock 数据与开发专用文件

| # | 文件 | 行数 | 说明 |
|---|------|------|------|
| 5 | `src\api\mock.ts` | 571 行 | 全量模拟数据源（4 个 Agent 目标、12 个攻击家族、5 层防御规则、2 条评估结果等） |
| 6 | `src\api\config.ts` | 4 行 | Mock/真实 API 切换开关（读取 `VITE_USE_MOCK`） |
| 7 | `src\api\attack.ts` | — | 当前仅调用 mock 函数（标记为 mock-only） |
| 8 | `src\api\target.ts` | — | 当前仅调用 mock 函数（标记为 mock-only） |

> README 明确说明：`attack.ts` 和 `target.ts` 目前为 mock-only，计划后续替换为真实 HTTP 调用。

---

## 五、空占位目录（未实现组件）

| # | 路径 | 说明 |
|---|------|------|
| 9 | `src\components\EvidenceViewer\` | 空目录 |
| 10 | `src\components\ExperimentTimeline\` | 空目录 |
| 11 | `src\components\TargetSelector\` | 空目录 |

---

## 六、依赖锁文件（可选清理）

| # | 文件 | 说明 |
|---|------|------|
| 12 | `package-lock.json` | npm lock（142 KB），若用 pnpm 则为冗余 |
| 13 | `pnpm-lock.yaml` | pnpm lock（99 KB） |
| 14 | `node_modules\` | 依赖目录（~251 个包），`pnpm install` 可重建 |

---

## 七、其他可清理文件

| # | 文件 | 说明 |
|---|------|------|
| 15 | `public\favicon.svg` / `icons.svg` | 与 `dist\` 内重复 |
| 16 | `src\assets\vite.svg` / `react.svg` / `hero.png` | Vite/React 默认图标，非项目自有 |

---

## 八、外部引用 / API Key 汇总

### 结论：零泄露，零归属引用

| 搜索项 | 结果 |
|------|------|
| API Key / Token / Secret | ❌ 无（唯一 `token:` 是 Ant Design 主题色配置） |
| GitHub 仓库引用 | ❌ 无 |
| arXiv / 论文链接 | ❌ 无 |
| 归属注释（inspired by / based on / credit） | ❌ 无 |
| 个人信息（邮箱 / 姓名） | ❌ 无 |
| 外部 URL（非 localhost） | ❌ 无 |
| DeepSeek API 地址 | ❌ 无（仅 UI 标签文字提及 "DeepSeek" 字样） |
| localhost URL | 7 处（mock 数据 4 个 + vite 代理 1 个 + UI placeholder 1 个 + README 1 个），全部开发用途 |

---

## 九、注释密度统计

| 文件 | 总行数 | 注释行 | 比例 |
|------|--------|--------|------|
| `api/types.ts` | 378 | 33 | 9% |
| `api/mock.ts` | 570 | 16 | 3% |
| `api/client.ts` | 19 | 1 | 5% |
| `api/config.ts` | 7 | 3 | 43% |
| `App.tsx` | 42 | 0 | 0% |
| `main.tsx` | 24 | 0 | 0% |
| `pages/Dashboard/index.tsx` | 202 | 4 | 2% |
| `pages/ExperimentCenter/index.tsx` | 536 | 7 | 1% |
| `pages/ResultAnalysis/index.tsx` | 538 | 11 | 2% |
| `pages/DefenseConfig/index.tsx` | 160 | 1 | 1% |
| `pages/TargetManagement/index.tsx` | 192 | 0 | 0% |
| `pages/AttackConfig/index.tsx` | 280 | 4 | 1% |
| `pages/VariantAnalysis/index.tsx` | — | — | <2% |
| `pages/AuditLog/index.tsx` | — | — | <2% |
| **平均** | | | **~2%** |

---

## 十、建议保留的核心文件清单

```
web\
├── index.html
├── package.json
├── pnpm-lock.yaml              # 或 package-lock.json，二选一
├── vite.config.ts
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── eslint.config.js
├── .env                        # 仅 VITE_USE_MOCK，无敏感内容
├── .gitignore
├── public\
│   ├── favicon.svg
│   └── icons.svg
└── src\
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── api\
    │   ├── client.ts
    │   ├── config.ts
    │   ├── types.ts
    │   ├── attack.ts           # ⚠️ 目前 mock-only
    │   ├── target.ts           # ⚠️ 目前 mock-only
    │   ├── defense.ts
    │   ├── experiment.ts
    │   ├── evaluation.ts
    │   └── mock.ts             # 若不提交可工作在后端模式
    ├── components\
    │   ├── AttackFamilyTag\
    │   ├── Layout\
    │   ├── MetricCard\
    │   └── (删除 3 个空目录)
    ├── pages\
    │   ├── AttackConfig\
    │   ├── AuditLog\
    │   ├── Dashboard\
    │   ├── DefenseConfig\
    │   ├── ExperimentCenter\
    │   ├── ResultAnalysis\
    │   ├── TargetManagement\
    │   └── VariantAnalysis\
    ├── store\
    │   ├── experimentStore.ts
    │   ├── targetStore.ts
    │   └── uiStore.ts
    └── utils\
        ├── colorMap.ts
        ├── constants.ts
        └── formatters.ts
```

> **前端风险远低于后端**：无 API Key 泄露，无外部归属引用，清理重点在于删除 `dist/`、`README.md`、`.claude/`、3 个空目录、`node_modules/`。
