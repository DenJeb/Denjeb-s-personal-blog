import type { components } from "@/lib/api/schema";

type MomentItem = components["schemas"]["MomentItem"];

export function MomentPreview({ moments }: { moments: MomentItem[] }) {
  if (moments.length === 0) {
    return <p className="side-empty">暂无动态。</p>;
  }

  return (
    <div className="moment-preview">
      {moments.map((moment) => (
        <article key={moment.id} className="moment-preview-item">
          <p className="moment-preview-text">{moment.content}</p>
          <time
            className="moment-preview-time"
            dateTime={moment.created_at}
          >
            {moment.created_at.slice(0, 10)}
          </time>
        </article>
      ))}
    </div>
  );
}
