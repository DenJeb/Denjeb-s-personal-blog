import "server-only";

import { headers } from "next/headers";

import { api } from "./client";
import type { components } from "./schema";

export type AdminMe = components["schemas"]["AdminMe"];
export type AdminDashboard = components["schemas"]["AdminDashboard"];
export type AdminPostList = components["schemas"]["AdminPostList"];
export type AdminPostDetail = components["schemas"]["AdminPostDetail"];

async function cookieHeaders(): Promise<{ Cookie: string }> {
  // Forward the raw header; re-serializing the signed session can change it.
  return { Cookie: (await headers()).get("cookie") ?? "" };
}

export async function getAdminMe(): Promise<AdminMe | null> {
  const { data, response } = await api.GET("/api/v1/admin/me", {
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载管理员信息失败");
  }
  return data;
}

export async function getAdminDashboard(): Promise<AdminDashboard | null> {
  const { data, response } = await api.GET("/api/v1/admin/dashboard", {
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载后台统计失败");
  }
  return data;
}

export async function getAdminPosts(page = 1): Promise<AdminPostList | null> {
  const { data, response } = await api.GET("/api/v1/admin/posts", {
    params: { query: { page } },
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载后台文章失败");
  }
  return data;
}

export async function getAdminPost(
  postId: number,
): Promise<AdminPostDetail | null> {
  const { data, response } = await api.GET(
    "/api/v1/admin/posts/{post_id}",
    {
      params: { path: { post_id: postId } },
      headers: await cookieHeaders(),
      cache: "no-store",
    },
  );

  if (response.status === 404) {
    return null;
  }
  if (!data) {
    throw new Error("加载文章失败");
  }
  return data;
}
