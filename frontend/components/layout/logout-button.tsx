"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { postJson } from "@/lib/api/browser";

export function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function logout() {
    setPending(true);
    try {
      await postJson("/api/v1/auth/logout", {});
      router.replace("/");
      router.refresh();
    } catch {
      // Keep the current header if the session already expired or the network
      // request failed; the user can retry or navigate to /account.
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
    >
      {pending ? "退出中…" : "退出"}
    </button>
  );
}
