import { readFileSync } from "node:fs";
import { createServer } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const dir = dirname(fileURLToPath(import.meta.url));
const fixture = (name) =>
  JSON.parse(readFileSync(join(dir, "..", "fixtures", name), "utf8"));

const site = fixture("site.json");
const me = fixture("me.json");
const posts = fixture("posts.json");
const postsEmpty = fixture("posts-empty.json");
const postDetail = fixture("post-detail.json");
const postDetailById = fixture("post-detail-by-id.json");
const postComments = fixture("post-comments.json");
const tags = fixture("tags.json");
const postsByTag = fixture("posts-by-tag.json");
const archive = fixture("archive.json");
const searchResults = fixture("search-results.json");
const searchEmpty = fixture("search-empty.json");
const moments = fixture("moments.json");
const guestbook = fixture("guestbook.json");
const adminMe = fixture("admin-me.json");
const adminDashboard = fixture("admin-dashboard.json");
const adminPosts = fixture("admin-posts.json");
const adminComments = fixture("admin-comments.json");
const adminMomentComments = fixture("admin-moment-comments.json");
const adminMoments = fixture("admin-moments.json");
const adminMessages = fixture("admin-messages.json");
const adminUsers = fixture("admin-users.json");
const adminUploads = fixture("admin-uploads.json");
const adminSecurity = fixture("admin-security.json");
const adminPostDetail = fixture("admin-post-detail.json");
const createdPosts = new Map();
let nextPostId = 100;
let pendingTotpSecret = null;
let nextMomentId = Math.max(0, ...adminMoments.items.map((item) => item.id)) + 1;

function resetState() {
  for (const [target, name] of [
    [adminComments, "admin-comments.json"],
    [adminMomentComments, "admin-moment-comments.json"],
    [adminMoments, "admin-moments.json"],
    [adminMessages, "admin-messages.json"],
    [adminUsers, "admin-users.json"],
    [adminUploads, "admin-uploads.json"],
  ]) {
    const fresh = fixture(name);
    target.items = fresh.items;
    target.meta = fresh.meta;
  }
  Object.assign(adminSecurity, fixture("admin-security.json"));
  createdPosts.clear();
  nextPostId = 100;
  pendingTotpSecret = null;
  nextMomentId = Math.max(0, ...adminMoments.items.map((item) => item.id)) + 1;
}

function currentSecurityState() {
  if (adminSecurity.totp_enabled) {
    return { totp_enabled: true, setup_secret: null, setup_uri: null };
  }
  if (pendingTotpSecret) {
    return {
      totp_enabled: false,
      setup_secret: pendingTotpSecret,
      setup_uri: `otpauth://totp/Blog:admin?secret=${pendingTotpSecret}&issuer=Blog`,
    };
  }
  return { totp_enabled: false, setup_secret: null, setup_uri: null };
}
const textFixture = (name) =>
  readFileSync(join(dir, "..", "fixtures", name), "utf8");
const rss = textFixture("rss.xml");
const sitemap = textFixture("sitemap.xml");
const robots = textFixture("robots.txt");

const CSRF_TOKEN = "test-csrf";
const SESSION_COOKIE =
  "blog_session=test-session; Path=/; HttpOnly; SameSite=Lax";
const CLEAR_SESSION_COOKIE =
  "blog_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax";

async function readJsonBody(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    return {};
  }
}

function writeCreated(response, message) {
  response.statusCode = 201;
  response.end(JSON.stringify({ ok: true, message }));
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1:8001");
  const method = request.method ?? "GET";
  const cookie = request.headers.cookie ?? "";
  const loggedIn = cookie.includes("blog_session=");
  const adminLoggedIn = cookie.includes("blog_session=admin-session");
  const csrfOk = (request.headers["x-csrf-token"] ?? "") === CSRF_TOKEN;
  response.setHeader("content-type", "application/json; charset=utf-8");

  if (url.pathname === "/healthz") {
    response.end(JSON.stringify({ status: "ok" }));
    return;
  }

  if (method === "POST" && url.pathname === "/__reset") {
    resetState();
    response.end(JSON.stringify({ ok: true }));
    return;
  }

  if (url.pathname === "/api/v1/site") {
    response.end(JSON.stringify(site));
    return;
  }

  if (url.pathname === "/api/v1/auth/csrf") {
    response.end(JSON.stringify({ csrf_token: CSRF_TOKEN }));
    return;
  }

  if (url.pathname === "/api/v1/auth/me") {
    response.end(JSON.stringify(loggedIn ? me : { user: null }));
    return;
  }

  if (method === "POST" && url.pathname === "/api/v1/admin/logout") {
    if (!adminLoggedIn) {
      response.statusCode = 401;
      response.end(JSON.stringify({ detail: "请先登录后台" }));
      return;
    }
    if (!csrfOk) {
      response.statusCode = 400;
      response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
      return;
    }
    response.setHeader("set-cookie", CLEAR_SESSION_COOKIE);
    response.end(JSON.stringify({ ok: true }));
    return;
  }

  if (url.pathname.startsWith("/api/v1/admin/")) {
    if (!adminLoggedIn) {
      response.statusCode = 401;
      response.end(JSON.stringify({ detail: "请先登录后台" }));
      return;
    }
    if (method !== "GET" && cookie.includes("write_expired=1")) {
      response.statusCode = 401;
      response.end(JSON.stringify({ detail: "请先登录后台" }));
      return;
    }
    if (url.pathname === "/api/v1/admin/me") {
      response.end(JSON.stringify(adminMe));
      return;
    }
    if (url.pathname === "/api/v1/admin/dashboard") {
      response.end(JSON.stringify(adminDashboard));
      return;
    }
    if (method === "GET" && url.pathname === "/api/v1/admin/posts") {
      response.end(JSON.stringify(adminPosts));
      return;
    }
    if (method === "POST" && url.pathname === "/api/v1/admin/posts") {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const body = await readJsonBody(request);
      const id = nextPostId++;
      const post = {
        id,
        title: String(body.title ?? ""),
        slug: String(body.slug ?? "") || `post-${id}`,
        summary: String(body.summary ?? ""),
        published_at: String(body.published_at ?? ""),
        is_published: Boolean(body.is_published),
        is_public: Boolean(body.is_published),
        tags: Array.isArray(body.tags) ? body.tags : [],
        reading_minutes: 1,
        content: String(body.content ?? ""),
        content_html: `<p>${String(body.content ?? "")}</p>`,
      };
      createdPosts.set(id, post);
      response.statusCode = 201;
      response.end(JSON.stringify(post));
      return;
    }
    if (method === "POST" && url.pathname === "/api/v1/admin/posts/preview") {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      response.end(
        JSON.stringify({ html: "<h1>Preview</h1><p>预览内容</p>" }),
      );
      return;
    }
    if (method === "POST" && url.pathname === "/api/v1/admin/uploads/inline") {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      response.end(
        JSON.stringify({
          url: "/static/uploads/mock.webp",
          markdown: "![图片](/static/uploads/mock.webp)",
        }),
      );
      return;
    }

    const postDetail = url.pathname.match(
      /^\/api\/v1\/admin\/posts\/(\d+)$/,
    );
    if (method === "GET" && postDetail) {
      if (cookie.includes("detail_expired=1")) {
        response.statusCode = 401;
        response.end(JSON.stringify({ detail: "请先登录后台" }));
        return;
      }
      const id = Number(postDetail[1]);
      const item = createdPosts.get(id) ?? (id === 1 ? adminPostDetail : null);
      if (!item) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "文章不存在！" }));
        return;
      }
      response.end(JSON.stringify(item));
      return;
    }
    if (method === "PUT" && postDetail) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const id = Number(postDetail[1]);
      const item = createdPosts.get(id);
      if (!item) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "文章不存在！" }));
        return;
      }
      const body = await readJsonBody(request);
      item.title = String(body.title ?? item.title);
      item.slug = String(body.slug ?? item.slug);
      item.summary = String(body.summary ?? item.summary);
      item.published_at = String(body.published_at ?? item.published_at);
      item.is_published = Boolean(body.is_published);
      item.is_public = item.is_published;
      item.tags = Array.isArray(body.tags) ? body.tags : item.tags;
      item.content = String(body.content ?? item.content);
      item.content_html = `<p>${item.content}</p>`;
      response.end(JSON.stringify(item));
      return;
    }
    if (method === "DELETE" && postDetail) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const id = Number(postDetail[1]);
      if (!createdPosts.delete(id)) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "文章不存在！" }));
        return;
      }
      response.statusCode = 204;
      response.end();
      return;
    }
    if (url.pathname === "/api/v1/admin/comments") {
      response.end(JSON.stringify(adminComments));
      return;
    }
    if (url.pathname === "/api/v1/admin/moment-comments") {
      response.end(JSON.stringify(adminMomentComments));
      return;
    }
    if (method === "GET" && url.pathname === "/api/v1/admin/moments") {
      response.end(JSON.stringify(adminMoments));
      return;
    }
    if (method === "GET" && url.pathname === "/api/v1/admin/messages") {
      response.end(JSON.stringify(adminMessages));
      return;
    }
    if (method === "GET" && url.pathname === "/api/v1/admin/users") {
      response.end(JSON.stringify(adminUsers));
      return;
    }
    if (method === "GET" && url.pathname === "/api/v1/admin/uploads") {
      response.end(JSON.stringify(adminUploads));
      return;
    }
    if (method === "GET" && url.pathname === "/api/v1/admin/security") {
      response.end(JSON.stringify(currentSecurityState()));
      return;
    }
    if (
      method === "POST" &&
      url.pathname === "/api/v1/admin/security/totp/start"
    ) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      if (!adminSecurity.totp_enabled) {
        pendingTotpSecret = "TESTSECRET";
      }
      response.end(JSON.stringify(currentSecurityState()));
      return;
    }
    if (
      method === "POST" &&
      url.pathname === "/api/v1/admin/security/totp/enable"
    ) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const body = await readJsonBody(request);
      if (String(body.code ?? "") !== "123456") {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "验证码不正确，请重试。" }));
        return;
      }
      adminSecurity.totp_enabled = true;
      pendingTotpSecret = null;
      response.end(
        JSON.stringify({ ok: true, message: "两步验证已启用。" }),
      );
      return;
    }
    if (
      method === "POST" &&
      url.pathname === "/api/v1/admin/security/totp/disable"
    ) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const body = await readJsonBody(request);
      if (
        !adminSecurity.totp_enabled ||
        !body.password ||
        String(body.code ?? "") !== "123456"
      ) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "密码或验证码不正确。" }));
        return;
      }
      adminSecurity.totp_enabled = false;
      response.end(
        JSON.stringify({ ok: true, message: "两步验证已关闭。" }),
      );
      return;
    }

    const userToggle = url.pathname.match(
      /^\/api\/v1\/admin\/users\/(\d+)\/toggle$/,
    );
    if (method === "POST" && userToggle) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const item = adminUsers.items.find(
        (user) => user.id === Number(userToggle[1]),
      );
      if (!item) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "用户不存在！" }));
        return;
      }
      item.is_active = !item.is_active;
      response.end(JSON.stringify({ ok: true, is_active: item.is_active }));
      return;
    }

    const userDelete = url.pathname.match(/^\/api\/v1\/admin\/users\/(\d+)$/);
    if (method === "DELETE" && userDelete) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const index = adminUsers.items.findIndex(
        (user) => user.id === Number(userDelete[1]),
      );
      if (index === -1) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "用户不存在！" }));
        return;
      }
      adminUsers.items.splice(index, 1);
      adminUsers.meta.total = adminUsers.items.length;
      adminUsers.meta.total_pages = 1;
      response.statusCode = 204;
      response.end();
      return;
    }

    if (method === "POST" && url.pathname === "/api/v1/admin/uploads/delete") {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const body = await readJsonBody(request);
      const path = String(body.path ?? "");
      if (!path) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "非法图片路径" }));
        return;
      }
      const index = adminUploads.items.findIndex(
        (file) => file.name === path,
      );
      if (index === -1) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "图片不存在" }));
        return;
      }
      if (adminUploads.items[index].referenced) {
        response.statusCode = 409;
        response.end(
          JSON.stringify({ detail: "图片仍被文章引用，不能删除。" }),
        );
        return;
      }
      adminUploads.items.splice(index, 1);
      adminUploads.meta.total = adminUploads.items.length;
      adminUploads.meta.total_pages = 1;
      response.end(JSON.stringify({ ok: true, message: "图片已删除。" }));
      return;
    }

    const momentDetail = url.pathname.match(
      /^\/api\/v1\/admin\/moments\/(\d+)$/,
    );
    if (method === "GET" && momentDetail) {
      if (cookie.includes("detail_expired=1")) {
        response.statusCode = 401;
        response.end(JSON.stringify({ detail: "请先登录后台" }));
        return;
      }
      const item = adminMoments.items.find(
        (moment) => moment.id === Number(momentDetail[1]),
      );
      if (!item) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "动态不存在！" }));
        return;
      }
      response.end(JSON.stringify(item));
      return;
    }
    if (method === "POST" && url.pathname === "/api/v1/admin/moments") {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const body = await readJsonBody(request);
      const content = String(body.content ?? "").trim();
      if (!content) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "动态内容不能为空。" }));
        return;
      }
      const item = {
        id: nextMomentId++,
        content,
        created_at: new Date().toISOString().slice(0, 19),
        public_page: 1,
      };
      adminMoments.items.unshift(item);
      adminMoments.meta.total = adminMoments.items.length;
      adminMoments.meta.total_pages = 1;
      response.statusCode = 201;
      response.end(JSON.stringify(item));
      return;
    }
    if (method === "PUT" && momentDetail) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const item = adminMoments.items.find(
        (moment) => moment.id === Number(momentDetail[1]),
      );
      if (!item) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "动态不存在！" }));
        return;
      }
      const body = await readJsonBody(request);
      item.content = String(body.content ?? "").trim();
      response.end(JSON.stringify(item));
      return;
    }
    if (method === "DELETE" && momentDetail) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const index = adminMoments.items.findIndex(
        (moment) => moment.id === Number(momentDetail[1]),
      );
      if (index === -1) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "动态不存在！" }));
        return;
      }
      adminMoments.items.splice(index, 1);
      adminMoments.meta.total = adminMoments.items.length;
      adminMoments.meta.total_pages = 1;
      response.statusCode = 204;
      response.end();
      return;
    }

    const messageDelete = url.pathname.match(
      /^\/api\/v1\/admin\/messages\/(\d+)$/,
    );
    if (method === "DELETE" && messageDelete) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const index = adminMessages.items.findIndex(
        (message) => message.id === Number(messageDelete[1]),
      );
      if (index === -1) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "留言不存在！" }));
        return;
      }
      adminMessages.items.splice(index, 1);
      adminMessages.meta.total = adminMessages.items.length;
      adminMessages.meta.total_pages = 1;
      response.statusCode = 204;
      response.end();
      return;
    }

    const commentApprove = url.pathname.match(
      /^\/api\/v1\/admin\/comments\/(\d+)\/approve$/,
    );
    if (method === "POST" && commentApprove) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const item = adminComments.items.find(
        (comment) => comment.id === Number(commentApprove[1]),
      );
      if (!item) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "评论不存在！" }));
        return;
      }
      item.is_approved = !item.is_approved;
      response.end(JSON.stringify({ ok: true, is_approved: item.is_approved }));
      return;
    }

    const commentDelete = url.pathname.match(
      /^\/api\/v1\/admin\/comments\/(\d+)$/,
    );
    if (method === "DELETE" && commentDelete) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const index = adminComments.items.findIndex(
        (comment) => comment.id === Number(commentDelete[1]),
      );
      if (index === -1) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "评论不存在！" }));
        return;
      }
      adminComments.items.splice(index, 1);
      adminComments.meta.total = adminComments.items.length;
      adminComments.meta.total_pages = 1;
      response.statusCode = 204;
      response.end();
      return;
    }

    const momentCommentApprove = url.pathname.match(
      /^\/api\/v1\/admin\/moment-comments\/(\d+)\/approve$/,
    );
    if (method === "POST" && momentCommentApprove) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const item = adminMomentComments.items.find(
        (comment) => comment.id === Number(momentCommentApprove[1]),
      );
      if (!item) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "动态评论不存在！" }));
        return;
      }
      item.is_approved = !item.is_approved;
      response.end(JSON.stringify({ ok: true, is_approved: item.is_approved }));
      return;
    }

    const momentCommentDelete = url.pathname.match(
      /^\/api\/v1\/admin\/moment-comments\/(\d+)$/,
    );
    if (method === "DELETE" && momentCommentDelete) {
      if (!csrfOk) {
        response.statusCode = 400;
        response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
        return;
      }
      const index = adminMomentComments.items.findIndex(
        (comment) => comment.id === Number(momentCommentDelete[1]),
      );
      if (index === -1) {
        response.statusCode = 404;
        response.end(JSON.stringify({ detail: "动态评论不存在！" }));
        return;
      }
      adminMomentComments.items.splice(index, 1);
      adminMomentComments.meta.total = adminMomentComments.items.length;
      adminMomentComments.meta.total_pages = 1;
      response.statusCode = 204;
      response.end();
      return;
    }
  }

  if (method === "POST" && url.pathname === "/api/v1/auth/login") {
    const body = await readJsonBody(request);
    if (body.email === "user@example.com" && body.password === "password") {
      response.setHeader("set-cookie", SESSION_COOKIE);
      response.end(JSON.stringify(me));
    } else {
      response.statusCode = 400;
      response.end(JSON.stringify({ detail: "邮箱或密码错误" }));
    }
    return;
  }

  if (method === "POST" && url.pathname === "/api/v1/auth/logout") {
    if (cookie.includes("logout-fail")) {
      response.statusCode = 500;
      response.end(JSON.stringify({ detail: "退出失败，请稍后重试。" }));
      return;
    }
    response.setHeader("set-cookie", CLEAR_SESSION_COOKIE);
    response.end(JSON.stringify({ ok: true }));
    return;
  }

  if (
    method === "POST" &&
    /^\/api\/v1\/posts\/[^/]+\/comments$/.test(url.pathname)
  ) {
    if (!loggedIn) {
      response.statusCode = 401;
      response.end(JSON.stringify({ detail: "请先登录" }));
      return;
    }
    if (!csrfOk) {
      response.statusCode = 400;
      response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
      return;
    }
    writeCreated(response, "评论已提交，审核通过后会显示。");
    return;
  }

  if (
    method === "POST" &&
    /^\/api\/v1\/moments\/[^/]+\/comments$/.test(url.pathname)
  ) {
    if (!loggedIn) {
      response.statusCode = 401;
      response.end(JSON.stringify({ detail: "请先登录" }));
      return;
    }
    if (!csrfOk) {
      response.statusCode = 400;
      response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
      return;
    }
    writeCreated(response, "评论已提交，审核通过后会显示。");
    return;
  }

  if (method === "POST" && url.pathname === "/api/v1/guestbook") {
    if (!loggedIn) {
      response.statusCode = 401;
      response.end(JSON.stringify({ detail: "请先登录" }));
      return;
    }
    if (!csrfOk) {
      response.statusCode = 400;
      response.end(JSON.stringify({ detail: "CSRF 校验失败" }));
      return;
    }
    writeCreated(response, "留言已提交。");
    return;
  }

  if (url.pathname === "/api/v1/tags") {
    response.end(JSON.stringify(tags));
    return;
  }

  if (url.pathname === "/api/v1/archive") {
    response.end(JSON.stringify(archive));
    return;
  }

  if (url.pathname === "/api/v1/search") {
    response.end(
      JSON.stringify(
        url.searchParams.get("q") === "FastAPI" ? searchResults : searchEmpty,
      ),
    );
    return;
  }

  if (url.pathname === "/api/v1/moments") {
    response.end(JSON.stringify(moments));
    return;
  }

  if (method === "GET" && url.pathname === "/api/v1/guestbook") {
    response.end(JSON.stringify(guestbook));
    return;
  }

  if (url.pathname === "/rss.xml") {
    response.setHeader("content-type", "application/rss+xml; charset=utf-8");
    response.end(rss);
    return;
  }

  if (url.pathname === "/sitemap.xml") {
    response.setHeader("content-type", "application/xml; charset=utf-8");
    response.end(sitemap);
    return;
  }

  if (url.pathname === "/robots.txt") {
    response.setHeader("content-type", "text/plain; charset=utf-8");
    response.end(robots);
    return;
  }

  if (url.pathname === "/api/v1/posts") {
    if (url.searchParams.get("tag")) {
      response.end(JSON.stringify(postsByTag));
      return;
    }
    response.end(
      JSON.stringify(url.searchParams.get("page") === "99" ? postsEmpty : posts),
    );
    return;
  }

  if (
    method === "GET" &&
    /^\/api\/v1\/posts\/[^/]+\/comments$/.test(url.pathname)
  ) {
    response.end(JSON.stringify(postComments));
    return;
  }

  const detailMatch = url.pathname.match(/^\/api\/v1\/posts\/([^/]+)$/);
  if (detailMatch) {
    const identifier = decodeURIComponent(detailMatch[1]);
    if (identifier === "missing") {
      response.statusCode = 404;
      response.end(JSON.stringify({ detail: "文章不存在！" }));
      return;
    }
    response.end(
      JSON.stringify(identifier === "42" ? postDetailById : postDetail),
    );
    return;
  }

  response.statusCode = 404;
  response.end(JSON.stringify({ detail: "Not Found" }));
});

server.listen(Number(process.env.MOCK_API_PORT ?? 8001), "127.0.0.1");
