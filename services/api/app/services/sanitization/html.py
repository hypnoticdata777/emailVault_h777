from __future__ import annotations

from dataclasses import dataclass
from html import escape, unescape
from html.parser import HTMLParser
from urllib.parse import urlparse


ALLOWED_TAGS = frozenset(
    {
        "a",
        "b",
        "blockquote",
        "br",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "i",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "table",
        "tbody",
        "td",
        "th",
        "thead",
        "tr",
        "u",
        "ul",
        "img",
    }
)
VOID_TAGS = frozenset({"br", "img"})
SKIP_CONTENT_TAGS = frozenset({"script", "style", "iframe", "object", "embed"})
BLOCK_TAGS = frozenset({"p", "div", "br", "li", "tr", "table", "blockquote", "pre"})
ALLOWED_ATTRS = {
    "a": frozenset({"href", "title"}),
    "img": frozenset({"src", "alt", "title", "width", "height"}),
    "td": frozenset({"colspan", "rowspan"}),
    "th": frozenset({"colspan", "rowspan"}),
}
SAFE_LINK_SCHEMES = frozenset({"http", "https", "mailto"})
SAFE_IMAGE_SCHEMES = frozenset({"cid", "data"})


@dataclass(frozen=True)
class SanitizedHtml:
    html: str
    plain_text: str
    blocked_remote_resources: int
    removed_tags: tuple[str, ...]


def sanitize_email_html(raw_html: str) -> SanitizedHtml:
    parser = _SafeEmailHtmlParser()
    parser.feed(raw_html)
    parser.close()
    sanitized_html = "".join(parser.output)
    plain_text = html_to_plain_text(sanitized_html)
    return SanitizedHtml(
        html=sanitized_html,
        plain_text=plain_text,
        blocked_remote_resources=parser.blocked_remote_resources,
        removed_tags=tuple(parser.removed_tags),
    )


def html_to_plain_text(raw_html: str) -> str:
    parser = _PlainTextParser()
    parser.feed(raw_html)
    parser.close()
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line).strip()


class _SafeEmailHtmlParser(HTMLParser):
    """Allow a small display-oriented subset and block email resource loading."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.blocked_remote_resources = 0
        self.removed_tags: list[str] = []
        self._skip_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in SKIP_CONTENT_TAGS:
            self._skip_stack.append(normalized)
            self.removed_tags.append(normalized)
            return
        if self._skip_stack:
            return
        if normalized not in ALLOWED_TAGS:
            self.removed_tags.append(normalized)
            return

        safe_attrs = self._safe_attrs(normalized, attrs)
        attr_text = "".join(f' {name}="{escape(value, quote=True)}"' for name, value in safe_attrs)
        self.output.append(f"<{normalized}{attr_text}>")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if self._skip_stack:
            if normalized == self._skip_stack[-1]:
                self._skip_stack.pop()
            return
        if normalized in ALLOWED_TAGS and normalized not in VOID_TAGS:
            self.output.append(f"</{normalized}>")

    def handle_data(self, data: str) -> None:
        if not self._skip_stack:
            self.output.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        self.handle_data(unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self.handle_data(unescape(f"&#{name};"))

    def _safe_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> list[tuple[str, str]]:
        safe: list[tuple[str, str]] = []
        allowed = ALLOWED_ATTRS.get(tag, frozenset())
        for raw_name, raw_value in attrs:
            name = raw_name.lower()
            value = raw_value or ""
            if name.startswith("on") or name == "style" or name not in allowed:
                continue
            if tag == "a" and name == "href" and not _has_safe_scheme(value, SAFE_LINK_SCHEMES):
                continue
            if tag == "img" and name == "src":
                if not _has_safe_scheme(value, SAFE_IMAGE_SCHEMES):
                    self.blocked_remote_resources += 1
                    continue
            safe.append((name, value))
        return safe


class _PlainTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _has_safe_scheme(value: str, safe_schemes: frozenset[str]) -> bool:
    parsed = urlparse(value.strip())
    if not parsed.scheme:
        return True
    return parsed.scheme.lower() in safe_schemes

