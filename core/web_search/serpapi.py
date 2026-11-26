import json
from urllib.parse import quote

import aiohttp
from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchError, WebSearchTool, format_web_results, result_rows


class SerpApiTool(WebSearchTool):
    async def request_engine(
        self,
        engine: str,
        payload: dict,
        *,
        country: str | None = None,
        search_lang: str | None = None,
    ) -> dict:
        """Search with one of the configured SerpApi engines.

        Args:
            engine: SerpApi search engine name.
            payload: Query parameters before adding authentication and locale.
            country: Optional Google country code.
            search_lang: Optional Google interface language.

        Returns:
            JSON results for the selected engine.

        Raises:
            WebSearchError: If SerpApi reports a request or application error.
        """
        params = {**payload, "engine": engine, "api_key": self.api_key}
        if country:
            params["gl"] = country
        if search_lang:
            params["hl"] = search_lang
        data = await self.request_json(
            "GET",
            "https://serpapi.com/search.json",
            headers={},
            params=params,
            timeout=aiohttp.ClientTimeout(total=60),
        )
        metadata = data.get("search_metadata")
        status = metadata.get("status") if isinstance(metadata, dict) else None
        if status == "Error" or (data.get("error") and status != "Success"):
            raise WebSearchError("SerpApi 拒绝了搜索请求")
        return data


@dataclass
class SerpApiWebSearchTool(SerpApiTool):
    name: str = "giftia_web_search_serpapi"
    description: str = (
        "Search the web using SerpApi Google Search for current information. "
        "Returns page titles, URLs, and snippets."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required. Search query."},
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return from the first page, 1-10. Default is 5; fewer may be available.",
                },
                "country": {
                    "type": "string",
                    "description": "Optional. Google country code, such as us, uk, or cn.",
                },
                "search_lang": {
                    "type": "string",
                    "description": "Optional. Google interface language code, such as en or zh-cn.",
                },
                "location": {
                    "type": "string",
                    "description": "Optional. Search origin, such as Austin, Texas, United States.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        max_results = max(1, min(int(kwargs.get("max_results", 5)), 10))
        payload = {"q": kwargs["query"]}
        if kwargs.get("location"):
            payload["location"] = kwargs["location"]
        data = await self.request_engine(
            "google",
            payload,
            country=kwargs.get("country"),
            search_lang=kwargs.get("search_lang"),
        )
        rows = [row for row in result_rows(data, "organic_results") if row.get("link")]
        return format_web_results(rows[:max_results], url_field="link")


@dataclass
class SerpApiNewsSearchTool(SerpApiTool):
    name: str = "giftia_news_search_serpapi"
    description: str = (
        "Search current news using the SerpApi Google News API. Returns article "
        "titles, source URLs, publishers, authors, snippets, and publication times."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Required. News search query. Google News operators such as site: and when: are supported.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum articles to return, 1-10. Default is 5; fewer may be available.",
                },
                "country": {
                    "type": "string",
                    "description": "Optional. Google News country code, such as us, uk, or cn.",
                },
                "search_lang": {
                    "type": "string",
                    "description": "Optional. Google News language code, such as en or zh-cn.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        max_results = max(1, min(int(kwargs.get("max_results", 5)), 10))
        data = await self.request_engine(
            "google_news",
            {"q": kwargs["query"].strip()},
            country=kwargs.get("country"),
            search_lang=kwargs.get("search_lang"),
        )
        results = []
        seen_urls = set()
        for group in result_rows(data, "news_results"):
            articles = [group] if group.get("link") else []
            if isinstance(group.get("highlight"), dict):
                articles.append(group["highlight"])
            articles.extend(result_rows(group, "stories"))
            for article in articles:
                url = article.get("link")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                source = article.get("source") or {}
                results.append(
                    {
                        "title": article.get("title") or "",
                        "url": url,
                        "snippet": article.get("snippet") or "",
                        "source": source.get("name") or source.get("title") or "",
                        "authors": source.get("authors") or [],
                        "published_at": article.get("iso_date")
                        or article.get("date")
                        or "",
                        "thumbnail_url": article.get("thumbnail")
                        or article.get("thumbnail_small")
                        or "",
                    }
                )
                if len(results) == max_results:
                    return json.dumps({"results": results}, ensure_ascii=False)
        return json.dumps({"results": results}, ensure_ascii=False)


@dataclass
class SerpApiImageSearchTool(SerpApiTool):
    name: str = "giftia_image_search_serpapi"
    description: str = (
        "Find images using SerpApi Google Images Light. Returns direct image URLs, "
        "thumbnails, dimensions, and source page URLs. Use image_url to display "
        "or send an image, and url to open its source page."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Required. Image search query.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum images to return, 1-10. Default is 5; fewer may be available.",
                },
                "country": {
                    "type": "string",
                    "description": "Optional. Google country code, such as us, uk, or cn.",
                },
                "search_lang": {
                    "type": "string",
                    "description": "Optional. Google interface language code, such as en or zh-cn.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        max_results = max(1, min(int(kwargs.get("max_results", 5)), 10))
        data = await self.request_engine(
            "google_images_light",
            {"q": kwargs["query"]},
            country=kwargs.get("country"),
            search_lang=kwargs.get("search_lang"),
        )
        results = []
        for item in result_rows(data, "images_results"):
            original_url = item.get("original") or ""
            thumbnail_url = item.get("thumbnail") or item.get("serpapi_thumbnail") or ""
            # Images from PDF results can use x-raw-image:// instead of a public URL.
            image_url = (
                original_url
                if original_url.startswith(("https://", "http://"))
                else thumbnail_url
            )
            if not image_url.startswith(("https://", "http://")):
                continue
            results.append(
                {
                    "title": item.get("title") or "",
                    "url": item.get("link") or image_url,
                    "snippet": item.get("source") or "",
                    "image_url": image_url,
                    "thumbnail_url": thumbnail_url,
                    "width": item.get("original_width")
                    if image_url == original_url
                    else None,
                    "height": item.get("original_height")
                    if image_url == original_url
                    else None,
                }
            )
            if len(results) == max_results:
                break
        return json.dumps({"results": results}, ensure_ascii=False)


@dataclass
class SerpApiFinanceSearchTool(SerpApiTool):
    name: str = "giftia_finance_search_serpapi"
    description: str = (
        "Look up stocks, indices, funds, currencies, and futures using Google Finance. "
        "Use ticker symbols such as AAPL:NASDAQ or currency pairs such as EUR-USD. "
        "Returns quote prices, currency, timestamps, key statistics, financials, "
        "and news when available. Set window only when price history is needed."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Required. Google Finance symbol, such as AAPL:NASDAQ, .INX:INDEXSP, BTC-USD, or EUR-USD.",
                },
                "search_lang": {
                    "type": "string",
                    "description": "Optional. Google interface language code, such as en or zh-cn.",
                },
                "window": {
                    "type": "string",
                    "enum": ["1D", "5D", "1M", "6M", "YTD", "1Y", "5Y", "MAX"],
                    "description": "Optional. Price history range. When set, Google Finance returns a quote summary and graph instead of full financials and news.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        query = kwargs["query"].strip()
        window = kwargs.get("window")
        if window and window not in self.parameters["properties"]["window"]["enum"]:
            return "Error: window must be one of 1D, 5D, 1M, 6M, YTD, 1Y, 5Y, MAX."
        payload = {"q": query}
        if window:
            payload["window"] = window
        data = await self.request_engine(
            "google_finance", payload, search_lang=kwargs.get("search_lang")
        )
        summary = data.get("summary") or {}
        result = {
            "results": [],
            "summary": summary,
            "knowledge_graph": data.get("knowledge_graph") or {},
            "financials": data.get("financials") or [],
            "news_results": data.get("news_results") or [],
            "suggestions": data.get("suggestions") or [],
        }
        if summary:
            metadata = data.get("search_metadata")
            url = (
                metadata.get("google_finance_url")
                if isinstance(metadata, dict)
                else None
            )
            result["results"].append(
                {
                    "title": summary.get("title") or query,
                    "url": url
                    or f"https://www.google.com/finance/quote/{quote(query, safe=':-.')}",
                    "snippet": json.dumps(summary, ensure_ascii=False),
                }
            )
        if window:
            result["graph"] = data.get("graph") or []
            result["key_events"] = data.get("key_events") or []
        return json.dumps(result, ensure_ascii=False)


@dataclass
class SerpApiScholarSearchTool(SerpApiTool):
    name: str = "giftia_scholar_search_serpapi"
    description: str = (
        "Search academic publications using Google Scholar. Returns titles, "
        "source URLs, snippets, publication details, citation counts, and available "
        "PDF or full-text links. Supports publication year filters."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Required. Academic search query.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum publications to return, 1-20. Default is 5.",
                },
                "search_lang": {
                    "type": "string",
                    "description": "Optional. Google Scholar interface language, such as en or zh-cn.",
                },
                "year_from": {
                    "type": "integer",
                    "description": "Optional. Earliest publication year, inclusive.",
                },
                "year_to": {
                    "type": "integer",
                    "description": "Optional. Latest publication year, inclusive.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        query = kwargs["query"].strip()
        max_results = max(1, min(int(kwargs.get("max_results", 5)), 20))
        payload = {"q": query, "num": max_results}
        for name, parameter in (("year_from", "as_ylo"), ("year_to", "as_yhi")):
            if kwargs.get(name) is not None:
                year = int(kwargs[name])
                if not 1 <= year <= 9999:
                    return "Error: publication years must be between 1 and 9999."
                payload[parameter] = year
        if payload.get("as_ylo", 1) > payload.get("as_yhi", 9999):
            return "Error: year_from must not be greater than year_to."
        data = await self.request_engine(
            "google_scholar", payload, search_lang=kwargs.get("search_lang")
        )
        results = []
        for item in result_rows(data, "organic_results")[:max_results]:
            resources = result_rows(item, "resources")
            url = item.get("link") or next(
                (resource["link"] for resource in resources if resource.get("link")),
                None,
            )
            # Some entries have publication details without a full text link.
            if not url:
                url = f"https://scholar.google.com/scholar?q={quote(item.get('title') or query, safe='')}"
            cited_by = (item.get("inline_links") or {}).get("cited_by") or {}
            results.append(
                {
                    "title": item.get("title") or "",
                    "url": url,
                    "snippet": item.get("snippet") or "",
                    "publication_info": item.get("publication_info") or {},
                    "cited_by_count": cited_by.get("total"),
                    "cited_by_url": cited_by.get("link"),
                    "resources": resources,
                }
            )
        return json.dumps({"results": results}, ensure_ascii=False)
