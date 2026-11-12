import { WriteForm } from "@/components/forms/write-form";
import type { components } from "@/lib/api/schema";
import { formatDateTime } from "@/lib/date";

type MomentItem = components["schemas"]["MomentItem"];

export function MomentCard({
  moment,
  isLoggedIn,
}: {
  moment: MomentItem;
  isLoggedIn: boolean;
}) {
  return (
    <article className="glass glass-hover moment-card">
      <time className="moment-date" dateTime={moment.created_at}>
        {formatDateTime(moment.created_at)}
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
                {formatDateTime(comment.created_at)}
              </time>
            </div>
          ))}
        </div>
      ) : null}

      <WriteForm
        endpoint={`/api/v1/moments/${moment.id}/comments`}
        maxLength={1000}
        isLoggedIn={isLoggedIn}
        nextPath={`/moments#moment-${moment.id}`}
        placeholder="写下你的评论…"
        buttonLabel="发表评论"
        loginPrompt="登录后评论"
      />
    </article>
  );
}
