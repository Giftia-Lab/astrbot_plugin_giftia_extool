import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from core.web_search import build_web_search_tools
from main import GiftiaExTool

API_KEY = "plugin-test-key"
QUERY = "网页搜索测试"
PAGE = "https://example.com/page"
RESULT = {"title": "标题", "url": PAGE, "snippet": "摘要"}
PAGE_TEXT = "这段来自网页正文。"


@pytest.fixture
def search_http(monkeypatch):
    response = MagicMock(status=200, headers={}, json=AsyncMock())
    session = MagicMock(timeout=aiohttp.ClientTimeout(total=300))
    session.request.return_value.__aenter__.return_value = response
    client = MagicMock()
    client.return_value.__aenter__.return_value = session
    monkeypatch.setattr("core.web_search.base.aiohttp.ClientSession", client)
    return session, response


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "arguments", "method", "endpoint", "payload", "headers", "body"),
    [
        (
            "tavily",
            {
                "max_results": 9,
                "search_depth": "advanced",
                "topic": "news",
                "days": 10,
                "time_range": "week",
                "start_date": "2026-10-01",
                "end_date": "2026-10-08",
            },
            "POST",
            "https://api.tavily.com/search",
            {
                "query": QUERY,
                "max_results": 9,
                "search_depth": "advanced",
                "topic": "news",
                "start_date": "2026-10-01",
                "end_date": "2026-10-08",
            },
            {"Authorization": f"Bearer {API_KEY}"},
            {"results": [{**RESULT, "content": "摘要", "index": "ignored"}]},
        ),
        (
            "bocha",
            {
                "count": 15,
                "summary": True,
                "freshness": "oneWeek",
                "include": "example.com",
                "exclude": "example.org",
            },
            "POST",
            "https://api.bochaai.com/v1/web-search",
            {
                "query": QUERY,
                "count": 15,
                "summary": True,
                "freshness": "oneWeek",
                "include": "example.com",
                "exclude": "example.org",
            },
            {"Authorization": f"Bearer {API_KEY}", "Accept-Encoding": "gzip, deflate"},
            {
                "data": {
                    "webPages": {
                        "value": [{"name": "标题", "url": PAGE, "summary": "摘要"}]
                    }
                }
            },
        ),
        (
            "brave",
            {"count": 18, "country": "DE", "search_lang": "de", "freshness": "week"},
            "GET",
            "https://api.search.brave.com/res/v1/web/search",
            {
                "q": QUERY,
                "count": 18,
                "country": "DE",
                "search_lang": "de",
                "freshness": "pw",
            },
            {"Accept": "application/json", "X-Subscription-Token": API_KEY},
            {
                "web": {
                    "results": [{"title": "标题", "url": PAGE, "description": "摘要"}]
                }
            },
        ),
        (
            "firecrawl",
            {"limit": 19, "location": "Beijing", "country": "CN", "timeout": 20000},
            "POST",
            "https://api.firecrawl.dev/v2/search",
            {
                "query": QUERY,
                "limit": 19,
                "sources": ["web"],
                "location": "Beijing",
                "country": "CN",
                "timeout": 20000,
            },
            {"Authorization": f"Bearer {API_KEY}"},
            {"success": True, "data": {"web": [RESULT]}},
        ),
        (
            "baidu_ai_search",
            {
                "top_k": 23,
                "search_recency_filter": "semiyear",
                "site": "example.com | example.net",
            },
            "POST",
            "https://qianfan.baidubce.com/v2/ai_search/web_search",
            {
                "messages": [{"role": "user", "content": QUERY}],
                "search_source": "baidu_search_v2",
                "resource_type_filter": [{"type": "web", "top_k": 23}],
                "search_recency_filter": "semiyear",
                "search_filter": {"match": {"site": ["example.com", "example.net"]}},
            },
            {
                "Authorization": f"Bearer {API_KEY}",
                "X-Appbuilder-Authorization": f"Bearer {API_KEY}",
            },
            {"references": [{"title": "标题", "url": PAGE, "content": "摘要"}]},
        ),
        (
            "exa",
            {
                "num_results": 17,
                "type": "neural",
                "category": "news",
                "include_domains": "example.com, example.net",
                "exclude_domains": "example.org",
                "start_published_date": "2026-10-01T00:00:00Z",
                "end_published_date": "2026-10-08T00:00:00Z",
            },
            "POST",
            "https://api.exa.ai/search",
            {
                "query": QUERY,
                "numResults": 17,
                "type": "neural",
                "category": "news",
                "includeDomains": ["example.com", "example.net"],
                "excludeDomains": ["example.org"],
                "startPublishedDate": "2026-10-01T00:00:00Z",
                "endPublishedDate": "2026-10-08T00:00:00Z",
                "contents": {"text": {"maxCharacters": 500}},
            },
            {"x-api-key": API_KEY},
            {"results": [{"title": "标题", "url": PAGE, "highlights": ["摘要"]}]},
        ),
        (
            "anysearch",
            {
                "max_results": 6,
                "tag": "academic.search",
                "zone": "global",
                "language": "zh-CN",
                "params": {"doi": "10.0000/example"},
            },
            "POST",
            "https://api.anysearch.com/v1/search",
            {
                "query": QUERY,
                "max_results": 6,
                "tag": "academic.search",
                "zone": "global",
                "language": "zh-CN",
                "params": {"doi": "10.0000/example"},
                "format": "json",
            },
            {"Authorization": f"Bearer {API_KEY}"},
            {"code": 0, "data": {"results": [RESULT]}},
        ),
        (
            "deepseek",
            {"count": 23, "ori_question": "请帮我查找资料", "need_content": True},
            "POST",
            "https://api.deepseek.com/v1/tools/search",
            {
                "query": QUERY,
                "count": 23,
                "ori_question": "请帮我查找资料",
                "need_content": True,
            },
            {"Authorization": f"Bearer {API_KEY}"},
            {
                "results": [
                    {
                        "title": "标题",
                        "url": PAGE,
                        "summary": "摘要",
                        "content": PAGE_TEXT,
                    }
                ]
            },
        ),
        (
            "serpapi",
            {
                "max_results": 1,
                "country": "cn",
                "search_lang": "zh-cn",
                "location": "Beijing",
            },
            "GET",
            "https://serpapi.com/search.json",
            {
                "engine": "google",
                "q": QUERY,
                "api_key": API_KEY,
                "gl": "cn",
                "hl": "zh-cn",
                "location": "Beijing",
            },
            {},
            {
                "organic_results": [
                    {"title": "标题", "link": PAGE, "snippet": "摘要"},
                    {"title": "Extra result", "link": "https://example.com/extra"},
                ]
            },
        ),
    ],
)
async def test_web_search_forwards_each_providers_parameters(
    search_http, provider, arguments, method, endpoint, payload, headers, body
):
    session, response = search_http
    response.json.return_value = body
    tool = build_web_search_tools(provider, [f" {API_KEY} "])[0]
    assert tool.parameters["required"] == ["query"]
    assert set(tool.parameters["properties"]) == {"query", *arguments}

    raw = await tool.call(None, query=QUERY, **arguments)

    session.request.assert_called_once()
    args, options = session.request.call_args
    assert args == (method, endpoint)
    assert options["allow_redirects"] is False
    assert options["json" if method == "POST" else "params"] == payload
    assert options["headers"] == headers
    expected = (
        {**RESULT, "snippet": f"摘要\n\n{PAGE_TEXT}"}
        if provider == "deepseek"
        else RESULT
    )
    assert json.loads(raw) == {"results": [expected]}
    assert API_KEY not in repr(tool)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider", "arguments", "endpoint", "payload", "headers", "body", "expected"),
    [
        (
            "tavily",
            {"extract_depth": "advanced"},
            "https://api.tavily.com/extract",
            {"urls": [PAGE], "extract_depth": "advanced"},
            {"Authorization": f"Bearer {API_KEY}"},
            {"results": [{"url": PAGE, "raw_content": PAGE_TEXT}]},
            f"URL: {PAGE}\nContent: {PAGE_TEXT}",
        ),
        (
            "firecrawl",
            {
                "format": "summary",
                "only_main_content": False,
                "timeout": 20000,
                "max_age": 0,
            },
            "https://api.firecrawl.dev/v2/scrape",
            {
                "url": PAGE,
                "formats": ["summary"],
                "onlyMainContent": False,
                "timeout": 20000,
                "maxAge": 0,
            },
            {"Authorization": f"Bearer {API_KEY}"},
            {"success": True, "data": {"summary": PAGE_TEXT}},
            f"URL: {PAGE}\nContent: {PAGE_TEXT}",
        ),
        (
            "exa",
            {"max_characters": 4000},
            "https://api.exa.ai/contents",
            {"ids": [PAGE], "text": {"maxCharacters": 4000}},
            {"x-api-key": API_KEY},
            {"results": [{"url": PAGE, "text": PAGE_TEXT}]},
            f"URL: {PAGE}\nContent: {PAGE_TEXT}",
        ),
        (
            "deepseek",
            {},
            "https://api.deepseek.com/v1/tools/fetch",
            {"url": PAGE},
            {"Authorization": f"Bearer {API_KEY}"},
            {"title": "标题", "content": PAGE_TEXT},
            f"URL: {PAGE}\nTitle: 标题\nContent: {PAGE_TEXT}",
        ),
    ],
)
async def test_extraction_tools_read_a_known_url(
    search_http, provider, arguments, endpoint, payload, headers, body, expected
):
    session, response = search_http
    response.json.return_value = body
    tool = build_web_search_tools(provider, [API_KEY])[1]
    assert tool.parameters["required"] == ["url"]
    assert set(tool.parameters["properties"]) == {"url", *arguments}

    result = await tool.call(None, url=PAGE, **arguments)

    session.request.assert_called_once_with(
        "POST", endpoint, allow_redirects=False, headers=headers, json=payload
    )
    assert result == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "engine", "payload", "body", "expected"),
    [
        (
            "news_search_serpapi",
            {"max_results": 2, "country": "cn", "search_lang": "zh-cn"},
            "google_news",
            {"gl": "cn", "hl": "zh-cn"},
            {
                "news_results": [
                    {
                        "highlight": {
                            "title": "标题",
                            "link": PAGE,
                            "snippet": "摘要",
                            "source": {"name": "示例日报", "authors": ["记者"]},
                            "iso_date": "2026-11-24T19:40:00Z",
                            "thumbnail": "https://example.com/news.jpg",
                        },
                        "stories": [{"link": PAGE, "title": "Duplicate"}],
                    }
                ]
            },
            {
                "results": [
                    {
                        **RESULT,
                        "source": "示例日报",
                        "authors": ["记者"],
                        "published_at": "2026-11-24T19:40:00Z",
                        "thumbnail_url": "https://example.com/news.jpg",
                    }
                ]
            },
        ),
        (
            "image_search_serpapi",
            {"max_results": 2, "country": "us", "search_lang": "en"},
            "google_images_light",
            {"gl": "us", "hl": "en"},
            {
                "images_results": [
                    {
                        "title": "标题",
                        "link": PAGE,
                        "source": "摘要",
                        "original": "x-raw-image://example",
                        "thumbnail": "https://example.com/thumb.png",
                        "original_width": 200,
                        "original_height": 100,
                    }
                ]
            },
            {
                "results": [
                    {
                        **RESULT,
                        "image_url": "https://example.com/thumb.png",
                        "thumbnail_url": "https://example.com/thumb.png",
                        "width": None,
                        "height": None,
                    }
                ]
            },
        ),
        (
            "finance_search_serpapi",
            {"search_lang": "en", "window": "1M"},
            "google_finance",
            {"hl": "en", "window": "1M"},
            {
                "summary": {"title": "Example quote", "price": 10},
                "search_metadata": {"google_finance_url": PAGE},
                "graph": [{"price": 10}],
                "key_events": [{"title": "Event"}],
            },
            {
                "results": [
                    {
                        "title": "Example quote",
                        "url": PAGE,
                        "snippet": json.dumps({"title": "Example quote", "price": 10}),
                    }
                ],
                "summary": {"title": "Example quote", "price": 10},
                "graph": [{"price": 10}],
                "key_events": [{"title": "Event"}],
                "knowledge_graph": {},
                "financials": [],
                "news_results": [],
                "suggestions": [],
            },
        ),
        (
            "scholar_search_serpapi",
            {
                "max_results": 13,
                "year_from": 2020,
                "year_to": 2025,
                "search_lang": "en",
            },
            "google_scholar",
            {"num": 13, "as_ylo": 2020, "as_yhi": 2025, "hl": "en"},
            {
                "organic_results": [
                    {
                        "title": "标题",
                        "snippet": "摘要",
                        "publication_info": {"summary": "Journal 2022"},
                        "resources": [{"link": PAGE, "file_format": "PDF"}],
                        "inline_links": {
                            "cited_by": {
                                "total": 12,
                                "link": "https://example.com/cited",
                            }
                        },
                    }
                ]
            },
            {
                "results": [
                    {
                        **RESULT,
                        "publication_info": {"summary": "Journal 2022"},
                        "resources": [{"link": PAGE, "file_format": "PDF"}],
                        "cited_by_count": 12,
                        "cited_by_url": "https://example.com/cited",
                    }
                ]
            },
        ),
    ],
)
async def test_serpapi_specialized_search_uses_its_own_engine(
    search_http, tool_name, arguments, engine, payload, body, expected
):
    session, response = search_http
    response.json.return_value = body
    tools = {tool.name: tool for tool in build_web_search_tools("serpapi", [API_KEY])}
    tool = tools[f"giftia_{tool_name}"]
    assert tool.parameters["required"] == ["query"]
    assert set(tool.parameters["properties"]) == {"query", *arguments}

    raw = await tool.call(None, query=QUERY, **arguments)

    session.request.assert_called_once()
    args, options = session.request.call_args
    assert args == ("GET", "https://serpapi.com/search.json")
    assert options["params"] == {
        **payload,
        "q": QUERY,
        "engine": engine,
        "api_key": API_KEY,
    }
    assert json.loads(raw) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "date_filter"),
    [
        ({"days": 8}, {"start_date": "2026-11-18"}),
        ({"time_range": "month"}, {"time_range": "month"}),
    ],
)
async def test_tavily_news_honors_relative_date_filters(
    search_http, monkeypatch, arguments, date_filter
):
    session, response = search_http
    response.json.return_value = {"results": []}
    monkeypatch.setattr(
        "core.web_search.tavily.date", MagicMock(today=lambda: date(2026, 11, 26))
    )

    await build_web_search_tools("tavily", [API_KEY])[0].call(
        None, query=QUERY, topic="news", **arguments
    )

    assert session.request.call_args.kwargs["json"] == {
        "query": QUERY,
        "max_results": 7,
        "search_depth": "basic",
        "topic": "news",
        **date_filter,
    }


@pytest.mark.asyncio
async def test_anysearch_retains_structured_results_in_anonymous_mode(search_http):
    session, response = search_http
    response.json.return_value = {
        "results": [{**RESULT, "publication": {"year": 2025}}]
    }

    result = await build_web_search_tools("anysearch", [])[0].call(None, query=QUERY)

    assert json.loads(result) == {
        "results": [{**RESULT, "snippet": '摘要\npublication: {"year": 2025}'}]
    }
    assert "Authorization" not in session.request.call_args.kwargs["headers"]


@pytest.mark.asyncio
async def test_missing_key_or_required_argument_does_not_call_provider(search_http):
    session, _ = search_http
    tool = build_web_search_tools("tavily", [])[0]
    assert "API 密钥" in await tool.call(None, query=QUERY)

    fetch = build_web_search_tools("deepseek", [API_KEY])[1]
    assert "url must" in await fetch.call(None)
    assert "url must" in await fetch.call(None, url="file:///tmp/local.html")
    session.request.assert_not_called()


@pytest.mark.asyncio
async def test_serpapi_transport_failure_does_not_expose_key(search_http):
    session, _ = search_http
    session.request.side_effect = aiohttp.InvalidURL(
        f"https://serpapi.com/search.json?api_key={API_KEY}"
    )

    search = build_web_search_tools("serpapi", [API_KEY, "backup-test-key"])[0]
    result = await search.call(None, query=QUERY)

    assert "请求失败" in result
    assert API_KEY not in result
    session.request.assert_called_once()


@pytest.mark.asyncio
async def test_search_and_extraction_share_round_robin_keys(search_http):
    session, response = search_http
    response.json.return_value = {"results": [{**RESULT, "raw_content": PAGE_TEXT}]}
    second_key = "second-test-key"
    search, extract = build_web_search_tools(
        "tavily", [f" {API_KEY} ", "  ", second_key, API_KEY]
    )

    await search.call(None, query=QUERY)
    await extract.call(None, url=PAGE)
    await search.call(None, query=QUERY)

    assert [
        call.kwargs["headers"]["Authorization"]
        for call in session.request.call_args_list
    ] == [f"Bearer {API_KEY}", f"Bearer {second_key}", f"Bearer {API_KEY}"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("retry_after", "cooldown"),
    [("8", 8), ("Fri, 27 Nov 2026 00:00:12 GMT", 12), ("invalid", 30)],
)
async def test_rate_limit_retries_with_new_key_and_observes_cooldown(
    search_http, monkeypatch, retry_after, cooldown
):
    session, response = search_http
    response.json.return_value = {"organic_results": []}
    throttled = MagicMock(status=429, headers={"Retry-After": retry_after})
    session.request.return_value.__aenter__.side_effect = [
        throttled,
        response,
        response,
        response,
    ]
    clock = MagicMock(return_value=100.0)
    monkeypatch.setattr("core.web_search.base.monotonic", clock)
    monkeypatch.setattr(
        "core.web_search.base.datetime",
        MagicMock(
            now=MagicMock(return_value=datetime(2026, 11, 27, tzinfo=timezone.utc))
        ),
    )
    backup_key = "backup-test-key"
    search = build_web_search_tools("serpapi", [API_KEY, backup_key])[0]

    result = await search.call(None, query=QUERY)
    assert json.loads(result) == {"results": []}
    clock.return_value += cooldown - 1
    await search.call(None, query=QUERY)
    clock.return_value += 1
    await search.call(None, query=QUERY)

    assert [call.kwargs["params"] for call in session.request.call_args_list] == [
        {"q": QUERY, "engine": "google", "api_key": key}
        for key in [API_KEY, backup_key, backup_key, API_KEY]
    ]


@pytest.mark.asyncio
async def test_retry_is_bounded_and_all_tools_skip_cooled_keys(search_http):
    session, response = search_http
    response.status = 429
    search, extract = build_web_search_tools(
        "tavily", [API_KEY, "key-two", "key-three"]
    )

    assert "限流" in await search.call(None, query=QUERY)
    assert session.request.call_count == 2
    assert "限流" in await extract.call(None, url=PAGE)
    assert [
        call.kwargs["headers"]["Authorization"]
        for call in session.request.call_args_list
    ] == [f"Bearer {API_KEY}", "Bearer key-two", "Bearer key-three"]

    assert "限流" in await search.call(None, query=QUERY)
    assert session.request.call_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403, 500])
async def test_other_http_errors_do_not_retry(search_http, status):
    session, response = search_http
    response.status = status
    search = build_web_search_tools("tavily", [API_KEY, "backup-test-key"])[0]

    assert f"HTTP {status}" in await search.call(None, query=QUERY)
    session.request.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("enabled", "provider", "expected_tools"),
    [
        (False, "tavily", []),
        (
            True,
            "tavily",
            ["giftia_web_search_tavily", "giftia_tavily_extract_web_page"],
        ),
        (
            True,
            "serpapi",
            [
                "giftia_web_search_serpapi",
                "giftia_news_search_serpapi",
                "giftia_image_search_serpapi",
                "giftia_finance_search_serpapi",
                "giftia_scholar_search_serpapi",
            ],
        ),
    ],
)
async def test_plugin_registers_only_the_selected_providers_tools(
    tmp_path, monkeypatch, enabled, provider, expected_tools
):
    monkeypatch.setattr("astrbot.api.star.StarTools.get_data_dir", lambda _: tmp_path)
    context = MagicMock()
    plugin = GiftiaExTool(
        context,
        {
            "web_search_config": {
                "enabled": enabled,
                "provider": provider,
                "api_keys": [API_KEY, "second-test-key"],
            }
        },
    )

    try:
        await plugin.initialize()
        if expected_tools:
            context.add_llm_tools.assert_called_once()
            tools = context.add_llm_tools.call_args.args
            assert [tool.name for tool in tools] == expected_tools
            assert tools[0].key_pool.keys == (API_KEY, "second-test-key")
            assert all(tool.key_pool is tools[0].key_pool for tool in tools)
        else:
            context.add_llm_tools.assert_not_called()
        context.get_config.assert_not_called()
    finally:
        await plugin.terminate()
