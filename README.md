# Denjeb 的个人博客

一个基于 FastAPI + Jinja2 服务端渲染的个人博客。前台提供文章浏览、标签、归档、搜索、RSS 和评论；后台提供内容管理、分类管理、评论审核、图片管理和用户管理。

## 功能概览

### 前台

- 首页、文章详情、标签、归档、搜索
- 文章与评论分页
- RSS（`/rss.xml?full=1` 输出全文）、sitemap、robots.txt
- SEO meta、canonical、Open Graph、文章 BlogPosting JSON-LD
- 暗色模式和响应式导航

### 账号

- 邮箱注册，验证码通过 SMTP 发送并存储在数据库中
- 邮箱 + 密码登录
- 邮箱 + 验证码登录
- 忘记密码、密码重置
- 账号自我注销，注销后该邮箱 24 小时内不能重新注册
- 密码重置、账号禁用或删除后，旧会话自动失效

### 评论

- 登录后可评论，默认进入待审核状态
- 管理员审核通过后公开显示
- 每用户 15 秒最多提交一条
- 支持评论分页

### 后台

- 唯一管理员登录，邮箱通过 `.env` 的 `ADMIN_EMAIL` 配置
- 仪表盘
- 文章、笔记 CRUD
- 文章草稿和未来日期定时发布（前台只显示已发布且日期已到的文章）
- 分类 CRUD，分类下有笔记时禁止删除
- 评论审核、删除
- 图片管理：引用状态、未引用图片清理
- 普通用户管理：禁用、启用、删除
- 管理员密码可通过 CLI 重置

### 内容与运维

- Markdown 渲染和 Pygments 代码高亮
- 图片上传，支持 JPG、PNG、GIF、WebP
- 内容 JSON 导出与恢复，可选清理未引用图片
- 完整备份：MySQL、上传图片、内容 JSON
- 空库迁移 + 备份恢复演练
- 健康检查 `/healthz`

### 安全

- Argon2 密码哈希
- CSRF 校验
- 数据库限流（登录、注册、重置、验证码、评论）
- Session 版本机制，支持会话撤销
- TrustedHost、Secure Cookie 配置
- 安全响应头和 CSP

## 技术栈

- Web：FastAPI + Jinja2
- 数据库：MySQL 8 + SQLAlchemy 2.x + Alembic
- Markdown：markdown-it-py + Pygments
- 登录：Session Cookie + Argon2
- 前端：Pico.css + 少量原生 JavaScript
- 测试与质量：pytest、Ruff、Black、GitHub Actions

## 目录结构

```text
个人博客/
├── app/
│   ├── main.py             应用入口、中间件、错误页
│   ├── config.py           环境配置
│   ├── db.py               数据库连接
│   ├── models.py           ORM 模型
│   ├── auth.py             后台登录依赖
│   ├── current_user.py     前台会话用户加载与失效清理
│   ├── rate_limit.py       数据库限流
│   ├── csrf.py             CSRF 校验
│   ├── markdown.py         Markdown 渲染
│   ├── content_io.py       内容导出/恢复
│   ├── backup.py           完整备份
│   ├── rehearse_restore.py 空库迁移 + 备份恢复演练
│   ├── routers/
│   │   ├── public.py       公开页面、评论、RSS、sitemap
│   │   ├── account.py      注册、登录、验证码、密码重置、注销
│   │   └── admin/          后台登录、内容、分类、评论、图片、用户管理
│   ├── templates/          Jinja2 模板
│   └── static/             CSS、JS、上传图片
├── migrations/             Alembic 迁移
├── tests/                  pytest 测试
├── deploy/                 Nginx、systemd 和部署文档
└── content/                本地内容备份（不提交）
```

## 项目状态

笔记后台 CRUD 已经可用，但笔记前台目前显示「整理中」，Obsidian 笔记导入和笔记 Markdown 渲染尚未开启。

部署、备份和上线检查等操作说明见 [`deploy/DEPLOY.md`](deploy/DEPLOY.md)。

## 许可证

本项目采用 [MIT License](LICENSE)。
