# API v1

`/api/v1` 供 Next.js 前台/后台和外部客户端使用。公开读接口无需登录；登录态、写接口和 `/admin/*` 读取接口需要 Session（后台接口还要求管理员 Session）。Jinja/HTMX 页面继续由 FastAPI 提供，两者共享 `app/services/` 业务逻辑。

## 约定

- 认证：公开只读接口不需要登录；`/api/v1/admin/*` 读取接口需要管理员 session。
- 编码：JSON，UTF-8。
- 分页：`page` 从 1 开始，`per_page` 默认按资源类型，最大 50。
- 错误：FastAPI 默认格式 `{"detail": "..."}`。
- 公开文章接口只返回已发布且日期已到的文章；后台文章接口例外，会返回草稿和未来文章。
- 时间：文章日期为 `YYYY-MM-DD`，评论/动态/留言为 ISO 8601。
- `/auth/me` 只读取前台用户 session，不返回管理员身份；后台读取接口在 `/api/v1/admin/*`，需要管理员 session（不是前台用户 session），未登录返回 401。
- 登录和写请求由浏览器同源直接调用 FastAPI；先 `GET /auth/csrf`，再把 token 放进 `X-CSRF-Token` 头。`Set-Cookie` 由 FastAPI 返回浏览器，不经过 Next.js。
- 未登录写请求返回 401；空内容或 CSRF 失败返回 400；15 秒内重复提交返回 429。文章/动态评论默认未审核，留言直接展示。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/site` | 站点名称、作者、对外地址 |
| GET | `/api/v1/auth/me` | 当前前台登录态；返回 `{"user": {"name": "..."} \| null}` |
| GET | `/api/v1/auth/csrf` | 获取与当前 session 绑定的 CSRF token |
| POST | `/api/v1/auth/login` | 邮箱 + 密码登录；成功设置 Session Cookie |
| POST | `/api/v1/auth/logout` | 退出当前前台用户 |
| GET | `/api/v1/posts` | 文章列表；支持 `page`、`per_page`、`tag`、`q` |
| GET | `/api/v1/posts/{slug-or-id}` | 文章详情，包含正文、HTML、目录、上下篇、相关文章 |
| GET | `/api/v1/posts/{slug-or-id}/comments` | 已审核评论分页 |
| GET | `/api/v1/tags` | 标签及文章数 |
| GET | `/api/v1/archive` | 按年/月分组的文章归档 |
| GET | `/api/v1/search?q=...` | 搜索文章标题、摘要、正文 |
| GET | `/api/v1/moments` | 动态及每条的已审核评论 |
| GET | `/api/v1/guestbook` | 留言分页 |
| GET | `/api/v1/recent?limit=5` | 最近文章（`limit` 1-20） |
| POST | `/api/v1/posts/{slug-or-id}/comments` | 发表评论（需登录 + CSRF；审核后展示） |
| POST | `/api/v1/moments/{id}/comments` | 发表动态评论（需登录 + CSRF；审核后展示） |
| POST | `/api/v1/guestbook` | 发表留言（需登录 + CSRF） |
| GET | `/api/v1/admin/me` | 当前管理员；未登录管理员返回 401 |
| GET | `/api/v1/admin/dashboard` | 后台统计：文章、动态、留言、评论、用户和待审核数 |
| GET | `/api/v1/admin/posts` | 后台文章列表（含草稿和未来文章），`page` 从 1 开始 |
| GET | `/api/v1/admin/posts/{id}` | 后台文章详情，包含原始 Markdown 和 HTML |

## 文章列表

```http
GET /api/v1/posts?page=1&per_page=5&tag=FastAPI
```

```json
{
  "items": [
    {
      "id": 1,
      "title": "博客开张：为什么用 FastAPI + Jinja2",
      "slug": "bo-ke-kai-zhang-wei-shi-yao-yong-fastapi-jinja2",
      "url": "https://yourdomain.com/posts/bo-ke-kai-zhang-wei-shi-yao-yong-fastapi-jinja2",
      "summary": "摘要",
      "published_at": "2026-10-30",
      "tags": ["FastAPI", "博客"],
      "reading_minutes": 3
    }
  ],
  "meta": {
    "page": 1,
    "per_page": 5,
    "total": 12,
    "total_pages": 3,
    "has_prev": false,
    "has_next": true
  }
}
```

## 文章详情

```http
GET /api/v1/posts/bo-ke-kai-zhang-wei-shi-yao-yong-fastapi-jinja2
```

在列表字段之外增加：

- `content`：原始 Markdown。
- `content_html`：服务端渲染后的 HTML，已禁用原始 HTML，可直接用于 `dangerouslySetInnerHTML`。
- `toc`：`[{level, text, id}]`，标题锚点与 `content_html` 中的 `id` 对应。
- `previous_post` / `next_post`：`{title, slug, url, published_at}` 或 `null`。
- `related_posts`：文章摘要列表（最多 3 篇）。

## 登录与写入

写请求由浏览器同源直接调用 FastAPI；先获取与当前 session 绑定的 CSRF token：

```http
GET /api/v1/auth/csrf
```

```json
{ "csrf_token": "..." }
```

登录（成功后 FastAPI 直接返回 `Set-Cookie`）：

```http
POST /api/v1/auth/login
Content-Type: application/json
X-CSRF-Token: <csrf_token>

{"email": "denjeb@example.com", "password": "..."}
```

```json
{ "user": { "name": "DenJeb" } }
```

发表评论 / 动态评论 / 留言：

```http
POST /api/v1/posts/{slug-or-id}/comments
Content-Type: application/json
X-CSRF-Token: <csrf_token>

{"content": "写点什么", "website": ""}
```

```json
{ "ok": true, "message": "评论已提交，审核通过后会显示。" }
```

`/api/v1/moments/{id}/comments` 和 `/api/v1/guestbook` 使用同样的 CSRF header 与 `{"content", "website"}` 结构。登出同理：

```http
POST /api/v1/auth/logout
X-CSRF-Token: <csrf_token>
```

失败约定：未登录 401；空内容或 CSRF 失败 400；15 秒内重复提交 429（带 `Retry-After`）。

## 后台 API（Phase 3a）

后台接口复用管理员登录 session。管理员先通过 FastAPI 的 `/admin/login` 完成邮箱 + 密码 + 验证码（可选 TOTP）流程，浏览器拿到 `blog_session` 后再访问：

```http
GET /api/v1/admin/dashboard
Cookie: blog_session=...
```

未登录管理员返回 `401 {"detail": "请先登录后台"}`，不会重定向。`/api/v1/admin/posts` 会返回草稿和未来文章，仅供后台使用。Next.js 服务端渲染 `/admin`、`/admin/posts` 时读取原始 `Cookie` 请求头转发给 FastAPI；不要重新序列化签名 Cookie。
目前只迁移了仪表盘和文章列表读取；文章编辑、评论/动态审核、用户与安全设置仍是 FastAPI 的 Jinja2 页面。

## Next.js 接入建议

1. **同源代理**：Nginx 把 `/api/` 转给 FastAPI，其余转给 Next。浏览器只访问同源路径，不产生 CORS。
2. **Cookie 不中转**：登录/登出由浏览器直接请求 FastAPI，`Set-Cookie` 由 FastAPI 返回浏览器；Next 服务端只读 Cookie 做 SSR，不要改成 JWT/localStorage。
3. **不要跨子域使用 `__Host-` Cookie**：`__Host-blog_session` 要求 Secure、Path=/ 且不能设置 Domain，适合同源路径代理。
4. **派生数据直接使用**：`content_html`、`toc`、`reading_minutes`、`prev/next`、`related_posts` 都由后端算好，Next 不需要重新实现 Markdown 和目录。
5. **写接口已接入**：登录/登出、评论、动态评论、留言已提供 JSON API；注册、邮箱验证码、找回密码、账户注销仍走 FastAPI 的 Jinja 页面。
6. **后台 SSR**：Next.js 服务端读取 `headers().get("cookie")` 的原始字符串转发给后台 API，不能重新序列化签名 Cookie。`next.config.ts` 的 `/admin` 反向代理放在 `afterFiles`，让 Next.js 已实现的 `/admin`、`/admin/posts` 优先，其余后台路径继续落到 FastAPI。
