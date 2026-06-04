# frontend · L01 人机交互（React）

AISECOPS 前端框架：Vite + React + TypeScript + Tailwind，**暖纸设计语言**
（见 [docs/design/frontend-design-language.md](../docs/design/frontend-design-language.md)）。

## 跑起来

```bash
# 1. 先起后端（仓库根目录）
make serve                 # FastAPI → localhost:8000

# 2. 起前端 dev（本目录）
cd frontend
npm install
npm run dev                # → http://localhost:5173（/api 自动代理到 8000）
```

登录：默认口令 **`aisecops`**（占位认证，真 RBAC 在 L02 平台核心做）。
用户名 `admin`→管理员、`analyst`→分析师、其他→普通查看。

## 结构

- `src/nav.ts` — 17 项导航（= 设计语言 IA）
- `src/auth.tsx` — 登录态 + 路由保护
- `src/components/Layout.tsx` — 侧栏 + 顶栏壳
- `src/pages/` — Login（登录页）/ Dashboard / Triage（端到端分诊）/ Settings（配置走 Web P-18）/ Placeholder
- 其余 14 个菜单页为占位，按设计语言逐步填充。

## 构建

```bash
npm run build              # → dist/
npm run typecheck          # tsc 类型检查
```
