# 上线前检查

## 现在已经开启 / 可用

- 邮件发送默认开启（`EMAIL_ENABLED=true`）；测试环境自动关闭，并跳过 `example.com` / `__pytest` 测试地址。
- 注册验证码、密码重置验证码、管理员通知 outbox 都会真实走 SMTP。
- 后台登录默认要求邮箱验证码（邮箱 + 密码 + 验证码），`ADMIN_LOGIN_CODE_ENABLED=true`。
- 管理员两步验证可用：登录后台 →「安全」→ 开始设置，用认证器扫描/录入密钥后输入验证码启用。
- Markdown 编辑器、图片上传/WebP 压缩、slug、目录、相关文章、阅读时长。
- 评论/留言/动态评论 HTMX 局部刷新，无 JavaScript 时仍可提交。
- 只读 `/api/v1` JSON API；本地 `DEBUG=true` 时可访问 `/docs`。
- Next.js 16 前台已实现：动态 SSR、Butterfly/Fluid 视觉、文章/动态/留言/搜索/归档；新增 `/api/v1/auth/me` 和管理员草稿预览。
- Next.js 后台日常页面已迁移：仪表盘、文章新建/编辑、评论/动态评论审核、动态、留言、用户、图片与安全设置；管理员登录和旧文章预览仍由 FastAPI 提供。
- CSP nonce、CSRF、数据库限流、评论审核、TOTP、异常日志。
- 备份、内容导出/恢复、空库恢复演练脚本。

## 上线前需要完成

- [ ] 安装依赖：`pip install -r requirements.txt`
- [ ] 执行迁移：`alembic upgrade head`
- [ ] 初始化管理员：`python -m app.create_admin`
- [ ] 生产 `.env` 设置：
  - `DEBUG=false`
  - `SESSION_HTTPS_ONLY=true`
  - `TRUSTED_HOSTS=yourdomain.com,www.yourdomain.com,127.0.0.1`（`127.0.0.1` 给 Next.js 服务端调用；staging 再加 staging 域名）
  - `SITE_URL=https://yourdomain.com`
  - `SITE_TIMEZONE=Asia/Shanghai`（确认评论/动态时间与文章发布判断符合预期）
  - `LEGACY_PUBLIC_SITE_ENABLED=false`（生产公开页面由 Next.js 提供）
  - `ADMIN_EMAIL`、`SECRET_KEY`、`DATABASE_URL`
  - `EMAIL_ENABLED=true`、`SMTP_*`
  - `ADMIN_LOGIN_CODE_ENABLED=true`
  - `MYSQLDUMP_PATH`
- [ ] 在后台「安全」页启用 TOTP，并妥善保存认证器
- [ ] 手动执行一次 `sudo -u www-data -H /srv/blog/.venv/bin/python -m app.backup`
- [ ] 执行一次恢复演练：`python -m app.rehearse_restore`
- [ ] 安装并启用 `blog-backup.timer`
- [ ] 安装并启用 `blog-offsite-backup.timer`，并用 `systemctl start blog-offsite-backup.service` 验证一次异地同步
- [ ] 用真实收件箱测试注册验证码、后台登录验证码和管理员通知，确认不进垃圾箱；自有域名发信时配置 SPF/DKIM/DMARC
- [ ] 安装并启用 `blog-notifications.timer`（SMTP 故障后自动补发通知）
- [ ] 用 `python -m app.create_admin --reset-totp` 验证丢失认证器时的恢复路径
- [ ] 确认 SMTP 故障时可通过服务器修改 `.env`：`ADMIN_LOGIN_CODE_ENABLED=false`，重启后再登录
- [ ] Next.js 前端：安装 Node.js 24 + npm；用 `frontend/.env.production.example` 创建 `.env.production`，设置 `API_BASE_URL` 和 `NEXT_PUBLIC_SITE_URL`（后者必须在 `npm run build` 前设置），然后 `npm ci && npm run build`
- [ ] 安装 `deploy/nextjs.service`（只监听 `127.0.0.1:3000`）；按 `deploy/DEPLOY.md` §12 用 `deploy/nginx.staging.conf` 验收 `/api/v1/site`、`/account`、`/healthz`、`/admin`、`/admin/posts`、`/admin/comments`、`/admin/moments`、`/admin/users`、`/admin/uploads`、`/admin/security`、`/admin/login`、`/login`、`/rss.xml`
- [ ] staging 的 FastAPI `.env` 中 `TRUSTED_HOSTS` 加 `127.0.0.1` 和 staging 域名；如果 staging 只用 HTTP，临时 `SESSION_HTTPS_ONLY=false`，正式切换恢复 `true`
- [ ] 生产切换：备份现有 `/etc/nginx/sites-available/blog`，替换为 `deploy/nginx.conf`，`nginx -t` 通过后再 `reload`；按 `DEPLOY.md` §13 验证
- [ ] HTTPS 下用真实浏览器验证 `__Host-blog_session`、`/login`、`/admin`、`/admin/posts` 和 Next.js 文章编辑器页
- [ ] 生产切换后再次测试注册/重置验证码、后台登录验证码、评论/留言写入和备份生成

## 等 HTTPS 上线后再打开

这些功能依赖 HTTPS 或正式域名，提前打开可能影响本地/上线流程：

- `SESSION_HTTPS_ONLY=true`：启用后 Session Cookie 变为 `__Host-blog_session`，本地 HTTP 无法登录。
- 应用层 HSTS：仅在 `SESSION_HTTPS_ONLY=true` 时发送；Nginx 配置已包含 HSTS。
- `DEBUG=false`：关闭 `/docs`、`/redoc`、`/openapi.json`，这是生产安全设置，不是功能缺失。
- Next.js 同源反向代理：按 `deploy/DEPLOY.md` §12 完成 staging 验收后，再按 §13 切换生产 Nginx；生产 `deploy/nginx.conf` 已包含 Next 路由，但不要提前 reload。

## 注意

`EMAIL_ENABLED=true` 时，`ADMIN_EMAIL` 必须是真实可收信地址，否则通知会退信。代码会跳过 `@example.com`、`@example.org`、`@example.net` 和 `__pytest` 开头的测试地址。

后台登录验证码依赖 SMTP。SMTP 故障时，如果管理员已启用 TOTP，系统会自动改用 TOTP 登录；未启用 TOTP 时可临时设置 `ADMIN_LOGIN_CODE_ENABLED=false` 并重启应用作为紧急入口。恢复 SMTP 后应立即改回 `true`。
