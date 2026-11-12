import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { AdminDeleteButton } from "@/components/admin/admin-delete-button";
import { MomentForm } from "@/components/admin/moment-form";
import { getAdminMoment } from "@/lib/api/admin";

export const metadata: Metadata = {
  title: "编辑动态 · 后台",
  robots: { index: false, follow: false },
};

export default async function EditMomentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const momentId = Number(id);
  if (!Number.isInteger(momentId) || momentId <= 0) {
    notFound();
  }

  const moment = await getAdminMoment(momentId);
  if (!moment) {
    notFound();
  }

  return (
    <>
      <header className="admin-page-head">
        <div>
          <h1>编辑动态</h1>
          <p>修改这条动态的内容。</p>
        </div>
      </header>

      <MomentForm momentId={moment.id} initialContent={moment.content} />

      <p>
        <AdminDeleteButton
          endpoint={`/api/v1/admin/moments/${moment.id}`}
          label="删除这条动态"
          confirmMessage="确定删除这条动态吗？"
          redirectTo="/admin/moments"
        />
      </p>
    </>
  );
}
