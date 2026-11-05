# 上线前检查

## 现在已经开启 / 可用

- 邮件发送默认开启（`EMAIL_ENABLED=true`）；测试环境自动关闭，并跳过 `example.com` / `__pytest` 测试地址。
- 注册验证码、密码重置验证码、管理员通知 outbox 都会真实走 SMTP。
- 后台登录默认要求邮箱验证码（邮箱 + 密码 + 验证码），`ADMIN_LOGIN_CODE_ENABLED=true`。
- 管理员两步验证可用：登录后台 →「安全」→ 开始设置，用认证器扫描/录入密钥后输入验证码启用。
- Markdown 编辑器、图片上传/WebP 压缩、slug、目录、相关文章、阅读时长。
- 评论/留言/动态评论 HTMX 局部刷新，无 JavaScript 时仍可提交。
- 只读 `/api/v1` JSON API；本地 `DEBUG=true` 时可访问 `/docs`。
- CSP nonce、CSRF、数据库限流、评论审核、TOTP、异常日志。
- 备份、内容导出/恢复、空库恢复演练脚本。

## 上线前需要完成

- [ ] 安装依赖：`pip install -r requirements.txt`
- [ ] 执行迁移：`alembic upgrade head`
- [ ] 初始化管理员：`python -m app.create_admin`
- [ ] 生产 `.env` 设置：
  - `DEBUG=false`
  - `SESSION_HTTPS_ONLY=true`
  - `TRUSTED_HOSTS=yourdomain.com,www.yourdomain.com`
  - `SITE_URL=https://yourdomain.com`
  - `ADMIN_EMAIL`、`SECRET_KEY`、`DATABASE_URL`
  - `EMAIL_ENABLED=true`、`SMTP_*`
  - `ADMIN_LOGIN_CODE_ENABLED=true`
  - `MYSQLDUMP_PATH`
- [ ] 在后台「安全」页启用 TOTP，并妥善保存认证器
- [ ] 测试一次后台登录验证码、注册验证码和管理员通知邮件
- [ ] 手动执行一次 `python -m app.backup`
- [ ] 执行一次恢复演练：`python -m app.rehearse_restore`
- [ ] 安装并启用 `blog-backup.timer`
- [ ] 用 `python -m app.create_admin --reset-totp` 验证丢失认证器时的恢复路径
- [ ] 确认 SMTP 故障时可通过服务器修改 `.env`：`ADMIN_LOGIN_CODE_ENABLED=false`，重启后再登录

## 等 HTTPS 上线后再打开

这些功能依赖 HTTPS 或正式域名，提前打开可能影响本地/上线流程：

- `SESSION_HTTPS_ONLY=true`：启用后 Session Cookie 变为 `__Host-blog_session`，本地 HTTP 无法登录。
- 应用层 HSTS：仅在 `SESSION_HTTPS_ONLY=true` 时发送；Nginx 配置已包含 HSTS。
- `DEBUG=false`：关闭 `/docs`、`/redoc`、`/openapi.json`，这是生产安全设置，不是功能缺失。
- Next.js 同源反向代理：等 Next 前台真正接入时再切换 Nginx 路由。

## 注意

`EMAIL_ENABLED=true` 时，`ADMIN_EMAIL` 必须是真实可收信地址，否则通知会退信。代码会跳过 `@example.com`、`@example.org`、`@example.net` 和 `__pytest` 开头的测试地址。

后台登录验证码依赖 SMTP。SMTP 故障时，如果管理员已启用 TOTP，系统会自动改用 TOTP 登录；未启用 TOTP 时可临时设置 `ADMIN_LOGIN_CODE_ENABLED=false` 并重启应用作为紧急入口。恢复 SMTP 后应立即改回 `true`。
