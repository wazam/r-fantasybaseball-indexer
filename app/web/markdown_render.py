import re

import markdown
import nh3
from markupsafe import Markup

_GIPHY_PATTERN = re.compile(r"!\[gif\]\(giphy\|([^|)]+)(?:\|[^)]*)?\)")
_SPOILER_PATTERN = re.compile(r">!(.+?)!<")
_SUPERSCRIPT_GROUP_PATTERN = re.compile(r"(?<!\\)\^\(([^)]*)\)")
_SUPERSCRIPT_WORD_PATTERN = re.compile(r"(?<!\\)\^(\S+)")

_ALLOWED_TAGS = {
    "p", "br", "b", "strong", "i", "em", "a", "ul", "ol", "li",
    "blockquote", "code", "pre", "del", "s",
    "table", "thead", "tbody", "tr", "th", "td", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
}
_ALLOWED_ATTRIBUTES = {"a": {"href"}}
_ALLOWED_SCHEMES = {"http", "https", "mailto"}

_md = markdown.Markdown(extensions=["tables", "pymdownx.tilde", "pymdownx.magiclink"])


def _convert_giphy(body: str) -> str:
    return _GIPHY_PATTERN.sub(r"[GIF](https://giphy.com/gifs/\1)", body)


def _convert_spoilers(body: str) -> str:
    return _SPOILER_PATTERN.sub(r"\1", body)


def _convert_superscript(body: str) -> str:
    body = _SUPERSCRIPT_GROUP_PATTERN.sub(lambda m: m.group(1).strip(), body)
    return _SUPERSCRIPT_WORD_PATTERN.sub(r"\1", body)


def render_markdown(body: str) -> Markup:
    if not body:
        return Markup("")

    text = _convert_giphy(body)
    text = _convert_spoilers(text)
    text = _convert_superscript(text)

    _md.reset()
    html = _md.convert(text)

    clean = nh3.clean(
        html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_SCHEMES,
    )
    return Markup(clean)
