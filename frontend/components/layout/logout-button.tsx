"use client";

import { useState } from "react";

import { ApiError, postJson } from "@/lib/api/browser";

export function LogoutButton() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function logout() {
    setPending(true);
    setError(null);
    try {
      await postJson("/api/v1/auth/logout", {});
      // Full reload so the server-rendered header drops the logged-in state.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/");
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
      {pending ? "退出中…" : error ? "重试退出" : "退出"}
    </button>
  );
}
