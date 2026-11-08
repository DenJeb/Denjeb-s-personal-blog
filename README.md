<div align="center">

# Denjeb 的个人博客

**记录文章、想法和日常**

![Version](https://img.shields.io/badge/version-1.6.0-blue)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

</div>

---

一个前后端分离的个人博客：**Next.js 16 前台 + FastAPI 后端**。
用 Markdown 写文章，记录零碎的想法，也欢迎留下评论和留言。

## 这里有什么

| 内容 | 说明 |
|---|---|
| 🖥️ **前台** | Next.js 16 App Router，动态 SSR，深蓝紫渐变 + 玻璃卡片，亮/暗色切换 |
| 📝 **文章** | Markdown 写作，支持标签、归档、搜索、目录、相关文章和 RSS |
| 💬 **动态** | 记录零碎的想法和日常 |
| ✍️ **留言** | 登录后在留言板留下想说的话 |
| 💭 **评论** | 文章和动态都支持评论，审核后展示 |
| 🔌 **API** | `/api/v1`：读接口公开；登录、评论、留言写入需要 Session + CSRF |
| ⚙️ **后台** | FastAPI + Jinja2 管理文章、动态、评论、留言和图片；邮箱 + 密码 + 验证码登录，可选 TOTP |

## 技术

**前台**：`Next.js 16` · `React 19` · `TypeScript` · `Tailwind CSS 4` · `openapi-fetch`
**后端**：`FastAPI` · `SQLAlchemy` · `MySQL` · `Alembic` · `Markdown` · `Pygments` · `Pillow`

## 目录

```
app/          FastAPI 后端、Jinja2 后台、公开 API
frontend/     Next.js 前台
deploy/       Nginx、systemd、部署/上线文档
docs/         API 与设计文档（本地文档，按仓库策略忽略）
tests/        后端 pytest
```

## 本地开发

### 1. 后端

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

后端与旧 Jinja2 站点：<http://localhost:8000>
API 文档（仅 `DEBUG=true`）：<http://localhost:8000/docs>

### 2. 前台

```bash
cd frontend
cp .env.example .env.local       # Windows: copy .env.example .env.local
npm install
npm run dev
```

新前台：<http://localhost:3000>

> 当前是 staging 阶段：新设计只在 Next.js 前台（:3000）。
> FastAPI 的 Jinja2 站点（:8000）和 `/admin`、账户页继续保留，直到 Nginx 切换。

环境变量：

```env
API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

`API_BASE_URL` 是运行时变量；`NEXT_PUBLIC_SITE_URL` 会在 `npm run build` 时内联，生产构建前必须先设置。

## 部署

- 后端：见 [deploy/DEPLOY.md](deploy/DEPLOY.md)
- Next.js staging：`deploy/nextjs.service` + `deploy/nginx.staging.conf`，步骤见 DEPLOY.md §12
- 上线前检查：见 [deploy/PRELAUNCH.md](deploy/PRELAUNCH.md)

## 关于

作者：DenJeb
这里记录我的文章、想法和日常。

博客正在持续建设中。代码和文章按 [Apache License 2.0](LICENSE) 授权。
