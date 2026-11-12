"use client";

import { AdminActionButton } from "./admin-action-button";

export function AdminDeleteButton({
  endpoint,
  label = "删除",
  confirmMessage = "确定删除吗？此操作不可撤销。",
  redirectTo,
  className,
}: {
  endpoint: string;
  label?: string;
  confirmMessage?: string;
  redirectTo?: string;
  className?: string;
}) {
  return (
    <AdminActionButton
      endpoint={endpoint}
      method="DELETE"
      label={label}
      confirmMessage={confirmMessage}
      redirectTo={redirectTo}
      className={className}
    />
  );
}
