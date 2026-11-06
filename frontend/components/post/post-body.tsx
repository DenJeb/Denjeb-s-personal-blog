export function PostBody({ html }: { html: string }) {
  // content_html is rendered by FastAPI with Markdown html=False; do not
  // re-render Markdown on the client, to keep one source of truth.
  return (
    <div
      className="post-content markdown-body mt-6"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
