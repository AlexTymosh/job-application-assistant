from app.jobs.normalisation import normalise_url


def test_normalise_url_lowercases_scheme_and_domain() -> None:
    assert (
        normalise_url("HTTPS://Example.COM/jobs/123") == "https://example.com/jobs/123"
    )


def test_normalise_url_removes_tracking_query_params() -> None:
    url = "https://example.com/jobs/123?utm_source=google&gclid=abc&keep=value"

    assert normalise_url(url) == "https://example.com/jobs/123?keep=value"


def test_normalise_url_removes_fragment() -> None:
    assert normalise_url("https://example.com/jobs/123#section") == (
        "https://example.com/jobs/123"
    )


def test_normalise_url_returns_none_for_empty_input() -> None:
    assert normalise_url(None) is None
    assert normalise_url("") is None
    assert normalise_url("   ") is None
