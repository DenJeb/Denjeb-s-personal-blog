"use client";

import { useState } from "react";

import { ApiError, postJson } from "@/lib/api/browser";

export function AdminLogoutButton() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function logout() {
    setPending(true);
    setError(null);
    try {
      await postJson("/api/v1/admin/logout", {});
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/admin/login");
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : "退出失败，请稍后重试。",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      type="button"
      className="btn btn-ghost"
      onClick={logout}
      disabled={pending}
      title={error ?? undefined}
    >
      {pending ? "退出中…" : error ? "重试退出" : "退出后台"}
    </button>
  );
}
