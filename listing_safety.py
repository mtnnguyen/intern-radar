"""Dependency-free safeguards for the public Markdown job board."""

import html
from urllib.parse import quote, urlsplit


def escape_table_cell(value):
    """Render untrusted job fields as plain text in one Markdown table cell."""
    text = str(value if value is not None else "")
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = " ".join(text.split())
    return html.escape(text, quote=False)


def safe_application_url(value):
    """Return a safe Markdown link destination, or None for invalid URLs."""
    if not isinstance(value, str) or not value or len(value) > 4096:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    if value != value.strip() or any(char.isspace() for char in value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"https", "http"}:
            return None
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return None
        if parsed.port is not None and not (1 <= parsed.port <= 65535):
            return None
        if any(char in parsed.netloc for char in "<>[]\\"):
            return None
    except ValueError:
        return None
    return quote(value, safe="/%:@?&=+#,;~!$'*-._")
