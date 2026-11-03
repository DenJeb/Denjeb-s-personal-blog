"""
========== Markdown 渲染 ==========
"""

from markdown_it import MarkdownIt
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from app.slugs import MAX_SLUG_LENGTH, slugify_text


def _highlight(code: str, lang: str, attrs: str) -> str:
    if not lang:
        return ""
    try:
        lexer = get_lexer_by_name(lang, stripall=False)
    except ClassNotFound:
        return ""
    return highlight(code, lexer, HtmlFormatter(nowrap=True))


md = MarkdownIt(
    "commonmark",
    {
        "html": False,
        "linkify": False,
        "typographer": False,
        "breaks": True,
        "highlight": _highlight,
    },
)
md.enable("table")
md.enable("strikethrough")
md.use(footnote_plugin)
md.use(tasklists_plugin, enabled=True)
md.use(deflist_plugin)


def _heading_text(token) -> str:
    return "".join(
        child.content
        for child in (token.children or [])
        if child.type in {"text", "code_inline"}
    ).strip()


def render_markdown_with_toc(text: str) -> tuple[str, list[dict]]:
    tokens = md.parse(text)
    headings: list[dict] = []
    used: set[str] = set()

    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        if index + 1 >= len(tokens) or tokens[index + 1].type != "inline":
            continue

        inline = tokens[index + 1]
        text_content = _heading_text(inline)
        base = slugify_text(text_content, fallback="section")
        slug = base
        counter = 2
        while slug in used:
            suffix = f"-{counter}"
            slug = f"{base[: MAX_SLUG_LENGTH - len(suffix)]}{suffix}"
            counter += 1
        used.add(slug)
        token.attrSet("id", slug)
        headings.append(
            {
                "level": int(token.tag[1]),
                "text": text_content or base,
                "id": slug,
            }
        )

    html = md.renderer.render(tokens, md.options, {})
    html = html.replace("<img ", '<img loading="lazy" decoding="async" ')
    return html, headings


def render_markdown(text: str) -> str:
    html, _ = render_markdown_with_toc(text)
    return html


def headings_for(text: str) -> list[dict]:
    _, headings = render_markdown_with_toc(text)
    return headings
