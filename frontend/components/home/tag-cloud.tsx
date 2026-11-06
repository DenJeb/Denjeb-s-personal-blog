import Link from "next/link";

import type { components } from "@/lib/api/schema";

type TagItem = components["schemas"]["TagItem"];

export function TagCloud({ tags }: { tags: TagItem[] }) {
  if (tags.length === 0) {
    return <p className="side-empty">暂无标签。</p>;
  }

  return (
    <div className="tag-cloud">
      {tags.map((tag) => (
        <Link
          key={tag.name}
          href={`/tags?tag=${encodeURIComponent(tag.name)}`}
          className="chip"
        >
          #{tag.name}
          <span>{tag.count}</span>
        </Link>
      ))}
    </div>
  );
}
