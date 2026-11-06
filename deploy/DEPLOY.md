# 部署清单

以下以 Ubuntu + Nginx + systemd 为例，路径统一假设为 `/srv/blog`，域名假设为 `yourdomain.com`。

## 1. 服务器准备

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip mysql-server nginx certbot python3-certbot-nginx git
```

安装 Python 3.13（如果系统源版本太旧，可用 deadsnakes 或源码编译）。

## 2. 部署代码

```bash
sudo mkdir -p /srv/blog
sudo chown -R $USER:$USER /srv/blog
cd /srv/blog
git clone <你的仓库地址> .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. 配置环境变量

```bash
cp .env.production.example .env
```

修改 `.env`：

- `DEBUG=false`
- `SESSION_HTTPS_ONLY=true`
- `TRUSTED_HOSTS=yourdomain.com,www.yourdomain.com,127.0.0.1`（`127.0.0.1` 给 Next.js 服务端调用 FastAPI 用；staging 再加 `staging.yourdomain.com`）
- `SECRET_KEY` 用随机长串
- `ADMIN_EMAIL` 填唯一管理员邮箱
- `SITE_URL=https://yourdomain.com`，用于邮件通知里的链接
- `EMAIL_ENABLED=true`；代码默认开启，测试环境会自动关闭
- `ADMIN_LOGIN_CODE_ENABLED=true`；后台登录默认要求邮箱验证码
- `DATABASE_URL` 填生产数据库
- `SMTP_*` 填真实邮件配置
- `MYSQLDUMP_PATH=/usr/bin/mysqldump`

## 4. 数据库

```sql
CREATE DATABASE blog CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'blog'@'localhost' IDENTIFIED BY '强密码';
GRANT ALL PRIVILEGES ON blog.* TO 'blog'@'localhost';
FLUSH PRIVILEGES;
```

```bash
cd /srv/blog
source .venv/bin/activate
alembic upgrade head
python -m app.create_admin
```

唯一管理员邮箱由 `.env` 的 `ADMIN_EMAIL` 指定，该命令只负责初始化和重置密码，不会创建其他管理员。

管理员忘记密码时：

```bash
python -m app.create_admin --reset
```

管理员丢失认证器、无法完成两步验证时：

```bash
python -m app.create_admin --reset-totp
```

该命令会关闭两步验证并撤销旧的后台会话。

如果需要恢复内容：

```bash
python -m app.content_io import --replace
```

内容备份 JSON 不在 Git 仓库中，需要单独安全传输到 `/srv/blog/content/content-backup.json`。

新评论、动态评论和留言会写入通知 outbox，并在请求结束后尝试发送。SMTP 暂时不可用或需要补发时：

```bash
python -m app.services.notifications send --limit 50
```

可以把这个命令加入 cron 或 systemd timer 定时执行。

完成后把目录交给服务用户，并保护 `.env`：

```bash
sudo chown -R www-data:www-data /srv/blog
sudo chmod 600 /srv/blog/.env
```

## 5. systemd

```bash
sudo cp deploy/blog.service /etc/systemd/system/blog.service
sudo systemctl daemon-reload
sudo systemctl enable --now blog
sudo systemctl status blog
```

日志：

```bash
journalctl -u blog -f
```

## 6. Nginx 与 HTTPS

先确认域名已经解析到服务器，然后用 HTTP 配置申请证书：

```bash
sudo cp deploy/nginx-http.conf /etc/nginx/sites-available/blog
sudo ln -s /etc/nginx/sites-available/blog /etc/nginx/sites-enabled/blog
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
```

证书生成后，切换到完整的 HTTPS 配置：

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/blog
sudo nginx -t
sudo systemctl reload nginx
```

把配置里的域名、证书路径和 `/srv/blog` 改成实际值。`nginx.conf` 里已经包含静态文件、限流、HSTS 和安全响应头。

`SESSION_HTTPS_ONLY=true` 时应用会使用 `__Host-blog_session` Cookie。`blog.service` 已经开启 `--proxy-headers`，请保留 Nginx 的 `X-Forwarded-Proto` 头，确保应用生成的绝对链接使用 HTTPS。

### 预留给 Next.js

当前 Nginx 把所有请求代理到 FastAPI。以后接入 Next.js 时，建议保持同源路径代理，不要直接让浏览器跨域调用 FastAPI：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000;
}

location /static/ {
    proxy_pass http://127.0.0.1:8000;
}

location / {
    proxy_pass http://127.0.0.1:3000;
}
```

这样 `/api/v1`、Session Cookie、CSRF 和 `__Host-` Cookie 都能继续工作；Next 服务端需要转发 FastAPI 的 Cookie，而不是改用 JWT/localStorage。

## 7. 防火墙

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 8. 每日备份

```bash
sudo cp deploy/blog-backup.service /etc/systemd/system/blog-backup.service
sudo cp deploy/blog-backup.timer /etc/systemd/system/blog-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now blog-backup.timer
systemctl list-timers blog-backup.timer
```

`app/backup.py` 会把 MySQL、上传图片和内容 JSON 写到 `/srv/blog/backups/<时间戳>/`，默认只保留最近 `BACKUP_KEEP=14` 个备份，并把备份目录权限设为 `700`。请把 `backups/` 定期复制到另一台机器或对象存储。

## 9. 恢复演练

不要直接拿正式库试恢复。先确认备份可用：

```bash
cd /srv/blog
source .venv/bin/activate
python -m app.rehearse_restore
```

它会取 `backups/` 里最新的备份，创建 `blog_rehearsal` 空库，执行 `alembic upgrade head`，恢复 `database.sql` 并打印各表行数；成功后自动删除演练库。需要人工检查时加 `--keep`。

数据库账号需要演练库的权限，用管理员执行一次：

```sql
GRANT ALL PRIVILEGES ON `blog_rehearsal`.* TO 'blog'@'localhost';
FLUSH PRIVILEGES;
```

## 10. 上线后检查

```bash
curl -I https://yourdomain.com/
curl https://yourdomain.com/healthz
curl -I https://yourdomain.com/static/css/pico.min.css
```

检查：

- `/healthz` 返回 `{"status":"ok"}`
- HTTPS 正常，HTTP 自动跳转
- 后台 `/admin/login` 可登录
- 注册验证码能收到邮件
- 图片上传和显示正常
- 备份目录生成成功

## 11. 更新流程

```bash
cd /srv/blog
source .venv/bin/activate
git pull
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart blog
```

上线前建议先跑：

```bash
pytest
ruff check app tests
black --check app tests
```

GitHub Actions 会在 push / PR 时用 MySQL 8 测试库执行同样的检查；本地未配置 `TEST_DATABASE_URL` 时，`pytest` 默认使用独立的 SQLite 测试文件，不会碰开发库。

## 12. Next.js 前台（staging）

第一阶段只把公开前台切到 Next.js，`/admin`、账户页、`/api`、`/static` 和 feed 仍由 FastAPI 提供。

先安装 Node.js 24 和 npm（例如 NodeSource 或 nvm），然后在 `/srv/blog/frontend` 创建 `.env.production`：

```env
API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=https://staging.yourdomain.com
```

> `NEXT_PUBLIC_SITE_URL` 会在 `npm run build` 时内联进产物（canonical、OG、`siteConfig.url`），**必须在 build 之前设置**；只在 systemd 里改它不会生效。`API_BASE_URL` 是运行时变量，可以放在 systemd 环境里。

然后再构建：

```bash
cd /srv/blog/frontend
npm ci
npm run build
```

同时确认 FastAPI 的 `.env` 里 `TRUSTED_HOSTS` 包含 `127.0.0.1` 和 `staging.yourdomain.com`；否则 Next.js 服务端请求会被 TrustedHostMiddleware 以 400 拒绝。

> staging 的 `nginx.staging.conf` 监听 HTTP 80。如果 FastAPI 的 `SESSION_HTTPS_ONLY=true`，`__Host-` Cookie 在 HTTP 下不可用，后台/账户登录会失败；staging 临时设为 `false`，正式切换前上 TLS 并改回 `true`。

安装 systemd 服务：

```bash
sudo cp deploy/nextjs.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nextjs
```

Nginx 使用 `deploy/nginx.staging.conf`（把域名和路径替换成实际值），只影响 staging：

```bash
sudo cp deploy/nginx.staging.conf /etc/nginx/sites-available/blog-staging
sudo ln -s /etc/nginx/sites-available/blog-staging /etc/nginx/sites-enabled/blog-staging
sudo nginx -t && sudo systemctl reload nginx
```

验收：

```bash
curl -s https://staging.yourdomain.com/api/v1/site
curl -I https://staging.yourdomain.com/
curl -I https://staging.yourdomain.com/admin
curl -I https://staging.yourdomain.com/login
```

`/api/v1/site` 应返回 JSON；`/admin`、`/login` 应返回 FastAPI 的 200/303，而不是 Next.js 404。
回滚时删除 staging server 的 `/` 反代，或把 `/` 重新指回 `127.0.0.1:8000`；生产 `deploy/nginx.conf` 在验收前不要修改。
