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
  const csrfOk = (request.headers["x-csrf-token"] ?? "") === CSRF_TOKEN;
  response.setHeader("content-type", "application/json; charset=utf-8");

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
