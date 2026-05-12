from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PREFIXES = ("utm_",)

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "msclkid",
}


def normalise_url(url: str | None) -> str | None:
    if url is None:
        return None

    stripped_url = url.strip()

    if not stripped_url:
        return None

    parts = urlsplit(stripped_url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in TRACKING_QUERY_KEYS
        and not any(key.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES)
    ]

    query = urlencode(filtered_query)

    path = parts.path.rstrip("/") or parts.path

    return urlunsplit((scheme, netloc, path, query, ""))
