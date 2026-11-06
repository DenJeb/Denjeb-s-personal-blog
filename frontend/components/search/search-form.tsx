export function SearchForm({ defaultValue = "" }: { defaultValue?: string }) {
  return (
    <form action="/search" method="get" className="search-form">
      <label htmlFor="search-q" className="sr-only">
        搜索关键词
      </label>
      <input
        id="search-q"
        name="q"
        defaultValue={defaultValue}
        maxLength={100}
        placeholder="搜索文章…"
        className="search-input"
      />
      <button type="submit" className="search-button">
        搜索
      </button>
    </form>
  );
}
