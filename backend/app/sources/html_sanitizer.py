"""Strict, provider-agnostic sanitizer for ATS job-description HTML.

The stored description retains only semantic formatting. Provider classes,
inline styles, images, forms, embeds, event handlers, and unsafe URLs are
intentionally discarded before the value can reach the API or frontend.
"""

from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

_ALLOWED_TAGS = {
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}
_VOID_TAGS = {"br", "hr"}
_DISCARDED_WITH_CONTENT = {
    "embed",
    "form",
    "iframe",
    "math",
    "noscript",
    "object",
    "script",
    "style",
    "svg",
    "template",
}
_SAFE_LINK_SCHEMES = {"http", "https", "mailto", "tel"}


def _safe_href(value: str | None) -> str | None:
    if not value:
        return None
    href = value.strip()
    try:
        parsed = urlsplit(href)
    except ValueError:
        return None
    if parsed.scheme.lower() not in _SAFE_LINK_SCHEMES:
        return None
    return href


class _JobHTMLSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.discarded_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self.discarded_stack:
            if tag in _DISCARDED_WITH_CONTENT:
                self.discarded_stack.append(tag)
            return
        if tag in _DISCARDED_WITH_CONTENT:
            self.discarded_stack.append(tag)
            return
        if tag not in _ALLOWED_TAGS:
            return

        if tag == "a":
            href = _safe_href(next((value for name, value in attrs if name.lower() == "href"), None))
            if href:
                self.parts.append(
                    f'<a href="{escape(href, quote=True)}" target="_blank" '
                    'rel="noopener noreferrer nofollow">'
                )
                return
        self.parts.append(f"<{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self.discarded_stack:
            if tag == self.discarded_stack[-1]:
                self.discarded_stack.pop()
            return
        if tag in _ALLOWED_TAGS and tag not in _VOID_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.discarded_stack:
            self.parts.append(escape(data, quote=False))


def sanitize_job_html(raw: object, *, decode_markup: bool = False) -> str:
    """Return semantic, inert HTML suitable for storage and display.

    ``decode_markup`` is reserved for providers such as Greenhouse that encode
    the description's HTML tags as entities. Stored descriptions must use the
    default so sanitizing them again at the API boundary remains idempotent.
    """
    if not isinstance(raw, str) or not raw.strip():
        return ""
    parser = _JobHTMLSanitizer()
    source = unescape(unescape(raw)) if decode_markup else raw
    parser.feed(source)
    parser.close()
    return "".join(parser.parts).strip()
