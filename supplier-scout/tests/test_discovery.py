from urllib.parse import quote

from app.services.discovery import _clean_result_url


def test_duckduckgo_redirect_is_unwrapped():
    target = "https://supplier.example/catalog"
    url = f"https://duckduckgo.com/l/?uddg={quote(target, safe='')}"

    assert _clean_result_url(url) == target


def test_blocked_hosts_are_rejected():
    assert _clean_result_url("https://www.avito.ru/example") is None
    assert _clean_result_url("https://maps.google.com/example") is None
