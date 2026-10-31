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
- `TRUSTED_HOSTS=yourdomain.com,www.yourdomain.com`
- `SECRET_KEY` 用随机长串
- `ADMIN_EMAIL` 填唯一管理员邮箱
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

如果需要恢复内容：

```bash
python -m app.content_io import --replace
```

内容备份 JSON 不在 Git 仓库中，需要单独安全传输到 `/srv/blog/content/content-backup.json`。

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

把配置里的域名、证书路径和 `/srv/blog` 改成实际值。`nginx.conf` 里已经包含静态文件、限流和安全响应头。

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
