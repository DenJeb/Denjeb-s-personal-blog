import "server-only";

import { headers } from "next/headers";
import { cache } from "react";

import { api } from "./client";
import type { components } from "./schema";

export type SiteInfo = components["schemas"]["SiteInfo"];
export type PostListResponse = components["schemas"]["PostListResponse"];
export type PostDetail = components["schemas"]["PostDetail"];
export type CommentListResponse = components["schemas"]["CommentListResponse"];
export type TagListResponse = components["schemas"]["TagListResponse"];
export type ArchiveResponse = components["schemas"]["ArchiveResponse"];
export type MomentListResponse = components["schemas"]["MomentListResponse"];
export type MessageListResponse = components["schemas"]["MessageListResponse"];

async function fetchSiteInfo(): Promise<SiteInfo> {
  const { data, error } = await api.GET("/api/v1/site", {
    cache: "no-store",
  });

  if (!data) {
    throw new Error(error ? "加载站点信息失败" : "站点信息为空");
  }

  return data;
}

async function fetchCurrentUser(): Promise<{ name: string } | null> {
  try {
    // Forward the raw Cookie header. Re-serializing via cookies().toString()
    // can change the signed session value, which the backend rejects.
    const cookieHeader = (await headers()).get("cookie") ?? "";
    const { data } = await api.GET("/api/v1/auth/me", {
      headers: { Cookie: cookieHeader },
      cache: "no-store",
    });

    return data?.user ?? null;
  } catch {
    return null;
  }
}

async function fetchPosts(
  params: {
    page?: number;
    perPage?: number;
    tag?: string;
    q?: string;
  } = {},
): Promise<PostListResponse> {
  const { data, error } = await api.GET("/api/v1/posts", {
    params: {
      query: {
        page: params.page,
        per_page: params.perPage,
        tag: params.tag,
        q: params.q,
      },
    },
    cache: "no-store",
  });

  if (!data) {
    throw new Error(error ? "加载文章列表失败" : "文章列表为空");
  }

  return data;
}

async function fetchPost(identifier: string): Promise<PostDetail | null> {
  const { data, response } = await api.GET("/api/v1/posts/{identifier}", {
    params: { path: { identifier } },
    cache: "no-store",
  });

  if (response.status === 404) {
    return null;
  }

  if (!data) {
    throw new Error("加载文章失败");
  }

  return data;
}

async function fetchPostComments(
  identifier: string,
  page = 1,
): Promise<CommentListResponse> {
  const { data, error } = await api.GET(
    "/api/v1/posts/{identifier}/comments",
    {
      params: { path: { identifier }, query: { page } },
      cache: "no-store",
    },
  );

  if (!data) {
    throw new Error(error ? "加载评论失败" : "评论为空");
  }

  return data;
}

async function fetchTags(): Promise<TagListResponse> {
  const { data, error } = await api.GET("/api/v1/tags", {
    cache: "no-store",
  });

  if (!data) {
    throw new Error(error ? "加载标签失败" : "标签为空");
  }

  return data;
}

async function fetchArchive(): Promise<ArchiveResponse> {
  const { data, error } = await api.GET("/api/v1/archive", {
    cache: "no-store",
  });

  if (!data) {
    throw new Error(error ? "加载归档失败" : "归档为空");
  }

  return data;
}

async function fetchSearch(
  q: string,
  page = 1,
): Promise<PostListResponse> {
  const { data, error } = await api.GET("/api/v1/search", {
    params: { query: { q, page } },
    cache: "no-store",
  });

  if (!data) {
    throw new Error(error ? "搜索失败" : "搜索为空");
  }

  return data;
}

async function fetchMoments(page = 1): Promise<MomentListResponse> {
  const { data, error } = await api.GET("/api/v1/moments", {
    params: { query: { page } },
    cache: "no-store",
  });

  if (!data) {
    throw new Error(error ? "加载动态失败" : "动态为空");
  }

  return data;
}

async function fetchGuestbook(
  page = 1,
): Promise<MessageListResponse> {
  const { data, error } = await api.GET("/api/v1/guestbook", {
    params: { query: { page } },
    cache: "no-store",
  });

  if (!data) {
    throw new Error(error ? "加载留言失败" : "留言为空");
  }

  return data;
}

// React cache() 只在单次请求/渲染内去重：文章页的 generateMetadata 和页面、
// 顶栏和页面里的 getSiteInfo/getCurrentUser 共享同一份结果，不会重复请求 FastAPI。
export const getSiteInfo = cache(fetchSiteInfo);
export const getCurrentUser = cache(fetchCurrentUser);
export const getPosts = cache(fetchPosts);
export const getPost = cache(fetchPost);
export const getPostComments = cache(fetchPostComments);
export const getTags = cache(fetchTags);
export const getArchive = cache(fetchArchive);
export const getSearch = cache(fetchSearch);
export const getMoments = cache(fetchMoments);
export const getGuestbook = cache(fetchGuestbook);
