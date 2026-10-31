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


def render_markdown(text: str) -> str:
    return md.render(text)
