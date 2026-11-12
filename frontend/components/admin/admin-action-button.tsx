"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, sendJson } from "@/lib/api/browser";

export function AdminActionButton({
  endpoint,
  method = "POST",
  body,
  label,
  pendingLabel = "处理中…",
  confirmMessage,
  redirectTo,
  className = "btn btn-ghost",
}: {
  endpoint: string;
  method?: "POST" | "DELETE";
  body?: unknown;
  label: string;
  pendingLabel?: string;
  confirmMessage?: string;
  redirectTo?: string;
  className?: string;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (confirmMessage && !window.confirm(confirmMessage)) {
      return;
    }

    setPending(true);
    setError(null);
    try {
      await sendJson(method, endpoint, body);
      if (redirectTo) {
        router.push(redirectTo);
        return;
      }
      router.refresh();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        router.push("/admin/login");
        return;
      }
      setError(
        caught instanceof ApiError ? caught.message : "操作失败，请稍后重试。",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className={className}
        onClick={run}
        disabled={pending}
        title={error ?? undefined}
      >
        {pending ? pendingLabel : error ? "重试" : label}
      </button>
      {error ? (
        <span role="alert" className="form-error">
          {error}
        </span>
      ) : null}
    </>
  );
}
