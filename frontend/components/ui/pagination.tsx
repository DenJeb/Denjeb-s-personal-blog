import Link from "next/link";

export function Pagination({
  page,
  totalPages,
  hasPrev,
  hasNext,
  buildHref,
}: {
  page: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
  buildHref: (page: number) => string;
}) {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <nav aria-label="分页" className="pagination">
      {hasPrev ? (
        <Link href={buildHref(page - 1)} className="page-link">
          上一页
        </Link>
      ) : (
        <span className="page-status">上一页</span>
      )}

      <span className="page-status">
        第 {page} / {totalPages} 页
      </span>

      {hasNext ? (
        <Link href={buildHref(page + 1)} className="page-link">
          下一页
        </Link>
      ) : (
        <span className="page-status">下一页</span>
      )}
    </nav>
  );
}
