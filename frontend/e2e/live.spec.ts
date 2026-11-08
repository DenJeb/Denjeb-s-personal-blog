import { expect, test } from "@playwright/test";

test.skip(
  !process.env.LIVE_API,
  "set LIVE_API=1 to run against a live FastAPI + Next.js",
);

test("public pages render against the live API", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });

  const pages: Array<[string, string]> = [
    ["/", "欢迎来到我的个人博客"],
    ["/posts", "文章"],
    ["/tags", "标签"],
    ["/archive", "归档"],
    ["/search", "搜索"],
    ["/moments", "动态"],
    ["/guestbook", "留言"],
    ["/login", "登录"],
    ["/about", "关于"],
  ];

  for (const [path, text] of pages) {
    await page.goto(path);
    await expect(page.getByText(text).first()).toBeVisible();
  }

  expect(errors).toEqual([]);
});
