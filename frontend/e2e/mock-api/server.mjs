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

const server = createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1:8001");
  response.setHeader("content-type", "application/json; charset=utf-8");

  if (url.pathname === "/api/v1/site") {
    response.end(JSON.stringify(site));
    return;
  }

  if (url.pathname === "/api/v1/auth/me") {
    const loggedIn = (request.headers.cookie ?? "").includes("blog_session=");
    response.end(JSON.stringify(loggedIn ? me : { user: null }));
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

  if (url.pathname === "/api/v1/guestbook") {
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

  if (/^\/api\/v1\/posts\/[^/]+\/comments$/.test(url.pathname)) {
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
