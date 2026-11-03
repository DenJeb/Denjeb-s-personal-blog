# Denjeb 的个人博客

**当前版本：1.5.0**

一个基于 FastAPI + Jinja2 服务端渲染的个人博客。前台提供文章浏览、动态、留言、标签、归档、搜索、RSS 和评论；后台提供文章、动态、留言、评论、图片和用户管理。

## 功能概览

### 前台

- 首页、文章列表/详情、动态、留言板、标签、归档、搜索
- 文章使用 `/posts/<slug>` 地址，旧 ID 地址自动 301
- 文章目录、上一篇/下一篇、相关文章、阅读时长、代码复制按钮
- 评论、留言和动态评论通过 HTMX 局部刷新，无 JavaScript 时仍可正常提交
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

### 动态与留言

- 管理员发布、编辑、删除动态
- 登录用户评论动态，评论先审核后公开
- 登录用户可以在留言板留言，留言立即公开
- 管理员可以审核动态评论、删除留言

### 后台

- 唯一管理员登录，邮箱通过 `.env` 的 `ADMIN_EMAIL` 配置
- 仪表盘
- 文章 CRUD
- Markdown 工具栏、服务端预览、拖拽/粘贴上传图片
- 文章草稿和未来日期定时发布（前台只显示已发布且日期已到的文章）
- 动态 CRUD、动态评论审核
- 留言管理
- 评论审核、删除
- 图片管理：引用状态、未引用图片清理
- 普通用户管理：禁用、启用、删除；注销或删除用户时级联删除其评论、动态评论和留言
- 管理员密码可通过 CLI 重置
- 管理员两步验证（TOTP），可在后台启用/关闭
- 新评论、动态评论和留言通过邮件通知管理员

### API

- 只读 JSON API `/api/v1`：文章、评论、标签、归档、搜索、动态、留言
- 与 Jinja/HTMX 页面共享 service 层；接口文档见 [`docs/api-v1.md`](docs/api-v1.md)
- 默认不启用 CORS，推荐 Next.js 通过同源反向代理接入

### 内容与运维

- Markdown 渲染和 Pygments 代码高亮
- 图片上传，支持 JPG、PNG、GIF、WebP；JPEG/PNG 自动转 WebP、限制长边 2000px
- 内容 JSON 导出与恢复，可选清理未引用图片
- 完整备份：MySQL、上传图片、内容 JSON
- 空库迁移 + 备份恢复演练
- 管理员通知 outbox，支持后台自动发送和手动补发
- `EMAIL_ENABLED` 控制是否真实发信；本地默认关闭，生产环境设为 `true`
- 健康检查 `/healthz`

### 安全

- Argon2 密码哈希
- CSRF 校验
- 数据库限流（登录、注册、重置、验证码、评论）
- Session 版本机制，支持会话撤销
- TrustedHost、Secure Cookie 配置
- 管理员 TOTP 两步验证
- CSP 使用每请求 nonce，不再允许内联脚本
- HSTS（生产环境）和 `__Host-` Session Cookie
- 未处理异常写入日志
- 安全响应头和 CSP

## 技术栈

- Web：FastAPI + Jinja2
- 数据库：MySQL 8 + SQLAlchemy 2.x + Alembic
- Markdown：markdown-it-py + Pygments
- 图片处理：Pillow
- Slug：python-slugify
- 两步验证：pyotp
- 登录：Session Cookie + Argon2
- 前端：Pico.css + HTMX + 少量原生 JavaScript
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
│   ├── services/
│   │   ├── accounts.py     验证码、注销邮箱锁、输入规则
│   │   ├── comments.py     评论/留言创建与通知
│   │   ├── content.py      文章可见性、slug、目录、相邻/相关文章
│   │   ├── notifications.py 管理员通知 outbox
│   │   └── uploads.py      图片处理与上传
│   ├── schemas/
│   │   └── public.py       API 响应模型
│   ├── routers/
│   │   ├── public.py       公开页面、评论、RSS、sitemap
│   │   ├── api/            只读 JSON API（/api/v1）
│   │   ├── account.py      注册、登录、验证码、密码重置、注销
│   │   └── admin/          后台登录、安全设置、文章、动态、留言、评论、图片、用户管理
│   ├── templates/          Jinja2 模板
│   └── static/             CSS、JS、上传图片
├── migrations/             Alembic 迁移
├── tests/                  pytest 测试
├── deploy/                 Nginx、systemd 和部署文档
└── content/                本地内容备份（不提交）
```

## 更新记录

### 1.5.0 (2026-11-03)

- 文章新增 slug 地址、目录、上一篇/下一篇、相关文章、阅读时长和代码复制。
- 评论、留言、动态评论和后台审核支持 HTMX 局部刷新。
- 管理员支持 TOTP 两步验证；新评论/留言通过 outbox 邮件通知。
- CSP 改为 per-request nonce；生产环境启用 HSTS 和 `__Host-` Cookie。
- 账号验证码、评论创建、文章内容逻辑抽取到 `app/services/`。
- 新增只读 `/api/v1` JSON API，为后续 Next.js 前台铺路。
- 新增 `EMAIL_ENABLED` 开关；测试环境默认关闭真实发信，避免退信。

### 1.4.0 (2026-11-03)

- 后台文章编辑器新增 Markdown 工具栏、服务端预览和拖拽/粘贴上传图片。
- 上传的 JPEG/PNG 自动纠正 EXIF 方向、限制长边 2000px 并转为 WebP。
- 上传逻辑抽取到 `app/services/uploads.py`。

### 1.3.1 (2026-11-01)

- 许可证从 MIT 改为 Apache License 2.0。

### 1.3.0 (2026-11-01)

- 新增动态和留言板。
- 用户注销时级联删除博客评论、动态评论和留言。
- 移除学习笔记和分类功能。
- 修复 MySQL 限流时区问题，限流事件统一使用 UTC。
- 内容 JSON 备份/恢复覆盖动态、动态评论和留言。
- 补全动态评论、后台预览和后台操作的分页处理。

## 项目状态

动态、留言和用户注销级联删除已经上线；学习笔记功能已移除。

部署、备份和上线检查等操作说明见 [`deploy/DEPLOY.md`](deploy/DEPLOY.md)。

## 许可证

Copyright 2026 DenJeb.

本项目采用 [Apache License 2.0](LICENSE)，代码和文章均按该协议授权。第三方依赖和资源遵循各自许可证。
