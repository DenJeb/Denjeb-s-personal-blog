# 公开 API v1

`/api/v1` 供 Next.js 前台和外部客户端使用。读接口公开；登录态和写接口需要 Session + CSRF。Jinja/HTMX 页面继续由 FastAPI 提供，两者共享 `app/services/` 业务逻辑。

## 约定

- 认证：只读接口不需要登录，只返回已发布且日期已到的文章。
- 编码：JSON，UTF-8。
- 分页：`page` 从 1 开始，`per_page` 默认按资源类型，最大 50。
- 错误：FastAPI 默认格式 `{"detail": "..."}`。
- 草稿和未来文章不会出现在 API 中，管理员登录也不会绕过。
- 时间：文章日期为 `YYYY-MM-DD`，评论/动态/留言为 ISO 8601。
- `/auth/me` 只读取前台用户 session，不返回管理员身份；管理员草稿预览仍是 `/admin/posts/{id}/preview` 的 HTML 路由，不在 API 中。
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

## Next.js 接入建议

1. **同源代理**：Nginx 把 `/api/` 转给 FastAPI，其余转给 Next。浏览器只访问 Next，不产生 CORS。
2. **BFF 转发 Cookie**：以后增加写接口时，Next 服务端转发 FastAPI 的 Session Cookie；不要改成 JWT/localStorage。
3. **不要跨子域使用 `__Host-` Cookie**：`__Host-blog_session` 要求 Secure、Path=/ 且不能设置 Domain，适合同源路径代理。
4. **派生数据直接使用**：`content_html`、`toc`、`reading_minutes`、`prev/next`、`related_posts` 都由后端算好，Next 不需要重新实现 Markdown 和目录。
5. **写接口后续再加**：评论、登录、留言先保持 Jinja 流程；Next 需要时在 `/api/v1` 增加对应 POST 接口，并设计 CSRF header/BFF 方案。
