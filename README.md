<div align="center">

# Denjeb 的个人博客

**记录学习、开发与生活**

[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js&logoColor=white&style=flat-square)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black&style=flat-square)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white&style=flat-square)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?logo=tailwindcss&logoColor=white&style=flat-square)](https://tailwindcss.com/)
<br />
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white&style=flat-square)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white&style=flat-square)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8-4479A1?logo=mysql&logoColor=white&style=flat-square)](https://www.mysql.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.1-D71F00?logo=sqlalchemy&logoColor=white&style=flat-square)](https://www.sqlalchemy.org/)
[![Nginx](https://img.shields.io/badge/Nginx-1.24-009639?logo=nginx&logoColor=white&style=flat-square)](https://nginx.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=flat-square)](LICENSE)

</div>

---

一个前后端分离的个人博客：**Next.js 16 前台 + FastAPI 后端**。  
用 Markdown 写文章，记录零碎的想法，也欢迎留下评论和留言。

## 功能

| 模块 | 内容 |
|---|---|
| 📝 **文章** | Markdown 写作、标签、目录、相关文章、归档、搜索、RSS |
| 💬 **动态** | 记录零碎的想法和日常 |
| ✍️ **互动** | 登录后评论、留言；评论审核后展示 |
| ⚙️ **后台** | 文章、评论、动态、用户、图片与安全设置；邮箱验证码 + 可选 TOTP |
| 🎨 **体验** | 响应式布局、亮/暗色切换、CSP、CSRF、数据库限流 |
| 🔌 **API** | `/api/v1`：公开读接口 + 登录/写入接口 + 后台只读接口 |

## 技术栈

| 层 | 技术 |
|---|---|
| 前台 | Next.js 16（App Router）· React 19 · TypeScript · Tailwind CSS 4 |
| 后端 | FastAPI · SQLAlchemy 2 · Alembic · MySQL 8 |
| 内容 | Markdown（markdown-it-py）· Pygments · Pillow |
| 认证 | Session Cookie · CSRF · 邮箱验证码 · 可选 TOTP |
| 部署 | Nginx · systemd · Let's Encrypt |

> 后台仪表盘和文章列表已迁移到 Next.js；文章编辑、审核、用户与安全设置仍由 FastAPI + Jinja2 提供。

## 项目结构

```text
.
├── app/                  FastAPI 后端
│   ├── routers/          公开、账户、后台与 /api/v1 路由
│   ├── services/         内容、账户、评论、上传、通知等业务逻辑
│   ├── templates/        Jinja2 管理页与旧前台模板
│   ├── static/           样式、脚本与上传图片
│   ├── models.py         SQLAlchemy 模型
│   └── main.py           应用入口与中间件
├── frontend/             Next.js 16 前台
│   ├── app/              App Router 页面（首页、文章、后台等）
│   ├── components/       页面组件
│   ├── lib/api/          API 客户端与 OpenAPI 生成类型
│   └── e2e/              Playwright 端到端测试
├── deploy/               Nginx、systemd、部署与上线检查
├── migrations/           Alembic 数据库迁移
├── scripts/              运维与开发辅助脚本
├── tests/                pytest 测试
├── docs/                 API 与设计文档
├── requirements.txt      Python 依赖
└── alembic.ini           Alembic 配置
```

## 本地开发

### 后端

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

- 后端 / 旧站点：<http://localhost:8000>
- API 文档（仅 `DEBUG=true`）：<http://localhost:8000/docs>

### 前台

```bash
cd frontend
cp .env.example .env.local       # Windows: copy .env.example .env.local
npm install
npm run dev
```

- 前台：<http://localhost:3000>

环境变量：

```env
API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

`API_BASE_URL` 是运行时变量；`NEXT_PUBLIC_SITE_URL` 会在 `npm run build` 时内联，生产构建前需要先设置。

## 测试

```bash
# 后端
pytest
ruff check app tests scripts
black --check app tests scripts

# 前台
cd frontend
npm run typecheck
npm run lint
npm test
npm run build
```

## API

接口说明见 [docs/api-v1.md](docs/api-v1.md)。修改后端路由后，可以重新生成前端类型：

```bash
cd frontend
npm run openapi:generate
```

## 部署

- 后端部署：见 [deploy/DEPLOY.md](deploy/DEPLOY.md)
- 上线前检查：见 [deploy/PRELAUNCH.md](deploy/PRELAUNCH.md)

生产环境使用 Nginx 同源代理，浏览器只访问一个域名；Next.js 与 FastAPI 由 systemd 管理。

## 关于

博客还在持续更新中。

- GitHub: [@DenJeb](https://github.com/DenJeb)
- Email: [denjeb@qq.com](mailto:denjeb@qq.com)

## License

本项目基于 [Apache License 2.0](LICENSE) 授权，© 2026 DenJeb。
