import "server-only";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { api } from "./client";
import type { components } from "./schema";

export type AdminMe = components["schemas"]["AdminMe"];
export type AdminDashboard = components["schemas"]["AdminDashboard"];
export type AdminPostList = components["schemas"]["AdminPostList"];
export type AdminPostDetail = components["schemas"]["AdminPostDetail"];
export type AdminCommentList = components["schemas"]["AdminCommentList"];
export type AdminMomentCommentList =
  components["schemas"]["AdminMomentCommentList"];
export type AdminMomentList = components["schemas"]["AdminMomentList"];
export type AdminMomentItem = components["schemas"]["AdminMomentItem"];
export type AdminMessageList = components["schemas"]["AdminMessageList"];
export type AdminUserList = components["schemas"]["AdminUserList"];
export type AdminUploadList = components["schemas"]["AdminUploadList"];
export type AdminSecurity = components["schemas"]["AdminSecurity"];

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
  const { data, response } = await api.GET("/api/v1/admin/posts/{post_id}", {
    params: { path: { post_id: postId } },
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    redirect("/admin/login");
  }
  if (response.status === 404) {
    return null;
  }
  if (!data) {
    throw new Error("加载文章失败");
  }
  return data;
}

export async function getAdminComments(
  page = 1,
): Promise<AdminCommentList | null> {
  const { data, response } = await api.GET("/api/v1/admin/comments", {
    params: { query: { page } },
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载评论失败");
  }
  return data;
}

export async function getAdminMomentComments(
  page = 1,
): Promise<AdminMomentCommentList | null> {
  const { data, response } = await api.GET("/api/v1/admin/moment-comments", {
    params: { query: { page } },
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载动态评论失败");
  }
  return data;
}

export async function getAdminMoments(
  page = 1,
): Promise<AdminMomentList | null> {
  const { data, response } = await api.GET("/api/v1/admin/moments", {
    params: { query: { page } },
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载动态失败");
  }
  return data;
}

export async function getAdminMoment(
  momentId: number,
): Promise<AdminMomentItem | null> {
  const { data, response } = await api.GET(
    "/api/v1/admin/moments/{moment_id}",
    {
      params: { path: { moment_id: momentId } },
      headers: await cookieHeaders(),
      cache: "no-store",
    },
  );

  if (response.status === 401) {
    redirect("/admin/login");
  }
  if (response.status === 404) {
    return null;
  }
  if (!data) {
    throw new Error("加载动态失败");
  }
  return data;
}

export async function getAdminMessages(
  page = 1,
): Promise<AdminMessageList | null> {
  const { data, response } = await api.GET("/api/v1/admin/messages", {
    params: { query: { page } },
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载留言失败");
  }
  return data;
}

export async function getAdminUsers(
  page = 1,
): Promise<AdminUserList | null> {
  const { data, response } = await api.GET("/api/v1/admin/users", {
    params: { query: { page } },
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载用户失败");
  }
  return data;
}

export async function getAdminUploads(
  page = 1,
): Promise<AdminUploadList | null> {
  const { data, response } = await api.GET("/api/v1/admin/uploads", {
    params: { query: { page } },
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载图片失败");
  }
  return data;
}

export async function getAdminSecurity(): Promise<AdminSecurity | null> {
  const { data, response } = await api.GET("/api/v1/admin/security", {
    headers: await cookieHeaders(),
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }
  if (!data) {
    throw new Error("加载安全设置失败");
  }
  return data;
}
