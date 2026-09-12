from urllib.parse import quote

from app.services.discovery import _clean_result_url


def test_duckduckgo_redirect_is_unwrapped():
    target = "https://supplier.example/catalog"
    url = f"https://duckduckgo.com/l/?uddg={quote(target, safe='')}"

    assert _clean_result_url(url) == target


def test_blocked_hosts_are_rejected():
    assert _clean_result_url("https://www.avito.ru/example") is None
    assert _clean_result_url("https://maps.google.com/example") is None


def test_bing_rss_parser_extracts_links():
    from app.services.discovery import _parse_bing_rss

    xml = """<?xml version=\"1.0\" encoding=\"utf-8\"?>
    <rss version=\"2.0\"><channel>
      <item><title>Поставщик</title><link>https://supplier.example/catalog</link></item>
      <item><title>Другой</title><link>https://second.example/</link></item>
    </channel></rss>"""

    assert _parse_bing_rss(xml) == [
        "https://supplier.example/catalog",
        "https://second.example/",
    ]


def test_bing_rss_parser_handles_invalid_xml():
    from app.services.discovery import _parse_bing_rss

    assert _parse_bing_rss("<rss><broken>") == []
