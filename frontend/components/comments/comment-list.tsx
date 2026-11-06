import type { components } from "@/lib/api/schema";

type CommentItem = components["schemas"]["CommentItem"];

export function CommentList({ comments }: { comments: CommentItem[] }) {
  if (comments.length === 0) {
    return <p className="side-empty">暂无评论。</p>;
  }

  return (
    <ul className="comment-list">
      {comments.map((comment) => (
        <li key={comment.id} className="comment-card">
          <div className="comment-author">{comment.author_name}</div>
          <div className="comment-body">{comment.content}</div>
          <time className="comment-time" dateTime={comment.created_at}>
            {comment.created_at}
          </time>
        </li>
      ))}
    </ul>
  );
}
