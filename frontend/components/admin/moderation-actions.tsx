"use client";

import { AdminActionButton } from "./admin-action-button";
import { AdminDeleteButton } from "./admin-delete-button";

export function ModerationActions({
  approveEndpoint,
  deleteEndpoint,
  approved,
}: {
  approveEndpoint: string;
  deleteEndpoint: string;
  approved: boolean;
}) {
  return (
    <div className="admin-row-actions">
      <AdminActionButton
        endpoint={approveEndpoint}
        label={approved ? "取消审核" : "通过"}
      />
      <AdminDeleteButton
        endpoint={deleteEndpoint}
        confirmMessage="确定删除这条评论吗？"
      />
    </div>
  );
}
