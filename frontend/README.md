# Next.js 前台

个人博客的 Next.js 16 App Router 前台。数据、认证、后台和业务逻辑仍在仓库根目录的 FastAPI 后端；这里只负责公开页面的渲染。

## 环境要求

- Node.js 24+
- npm 11+
- 后端 FastAPI 运行在 `http://127.0.0.1:8000`

## 本地开发

```bash
cp .env.example .env.local      # Windows: copy .env.example .env.local
npm install
npm run dev
```

打开 <http://localhost:3000>。

```env
API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

- `API_BASE_URL`：Next.js 服务端调用 FastAPI 的内网地址，运行时读取。
- `NEXT_PUBLIC_SITE_URL`：站点对外地址，**build 时内联**到 canonical / OG / `siteConfig`；生产构建前必须设置。

开发环境通过 `next.config.ts` 的 rewrites 把 `/api`、`/static`、`/admin`、`/login` 等路径代理到 FastAPI，保证浏览器只面对 `:3000` 一个源。

## 常用脚本

| 命令 | 作用 |
|---|---|
| `npm run dev` | 开发服务器（Turbopack） |
| `npm run build` | 生产构建 |
| `npm run start` | 启动生产构建 |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript 检查 |
| `npm test` | Vitest 单元测试 |
| `npm run openapi:generate` | 导出 OpenAPI 并生成 `lib/api/schema.d.ts`（需先激活仓库根目录的 `.venv`） |

## 目录

```
app/                 页面路由、布局、metadata
components/          layout / home / post / comments / moments / ui
lib/api/             openapi-fetch 客户端、fetcher、生成的 schema
lib/page-metadata.ts 每页 title / canonical / OG / RSS link
e2e/                 Playwright 测试与 mock API
proxy.ts             Next 16 Proxy：CSP nonce + 安全头
next.config.ts       dev rewrites、安全响应头
```

## API 类型

`lib/api/schema.d.ts` 由 FastAPI 的 OpenAPI schema 生成。后端接口变化后运行：

```bash
# 先激活仓库根目录的 .venv
npm run openapi:generate
```

## 测试

```bash
npm test                 # Vitest
npx playwright test      # 默认：mock API + next dev，使用本机 Edge
```

其他配置：

- `playwright.prod.config.ts`：对生产构建做状态码 / CSP 检查（:3100）。
- `playwright.error.config.ts`：模拟 FastAPI 500，验证错误页（:3200）。
- `playwright.live.config.ts`：对已启动的 FastAPI + Next 做 live smoke；需 `LIVE_API=1`。

## 说明

- 第一版是动态 SSR（`cache: "no-store"`），不做 ISR / on-demand revalidation。
- `/admin`、`/login`、`/register` 等账户页仍由 FastAPI + Jinja2 提供；Nginx 切换前生产环境也直接路由到 FastAPI。
- 文章正文使用后端返回的 `content_html`（`html=False` 渲染），前端不重新解析 Markdown。
- 设计方向：Butterfly / Fluid 风（深蓝紫渐变、玻璃卡片、hero + 侧栏），阅读页保持窄正文栏。
