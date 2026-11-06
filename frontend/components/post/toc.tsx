import type { components } from "@/lib/api/schema";

type TocItem = components["schemas"]["TocItem"];

export function Toc({ items }: { items: TocItem[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <nav aria-label="目录" className="glass side-card toc">
      <h2 className="toc-title">目录</h2>
      <ul className="toc-list">
        {items.map((item) => (
          <li
            key={item.id}
            style={{ paddingLeft: `${Math.max(item.level - 2, 0)}rem` }}
          >
            <a href={`#${item.id}`}>{item.text}</a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
