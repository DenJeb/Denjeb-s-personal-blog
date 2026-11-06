import type { components } from "@/lib/api/schema";

type MomentItem = components["schemas"]["MomentItem"];

export function MomentCard({ moment }: { moment: MomentItem }) {
  return (
    <article className="glass glass-hover moment-card">
      <time className="moment-date" dateTime={moment.created_at}>
        {moment.created_at}
      </time>

      <p className="moment-text">{moment.content}</p>

      <div className="moment-meta">{moment.comment_count} 条评论</div>

      {moment.comments.length > 0 ? (
        <div className="moment-comments">
          {moment.comments.map((comment) => (
            <div key={comment.id} className="moment-comment">
              <div className="moment-comment-author">{comment.author_name}</div>
              <div className="moment-comment-text">{comment.content}</div>
              <time
                className="moment-comment-time"
                dateTime={comment.created_at}
              >
                {comment.created_at}
              </time>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}
