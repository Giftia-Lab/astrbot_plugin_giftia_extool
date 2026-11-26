from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchError, WebSearchTool, format_web_results, result_rows


@dataclass
class FirecrawlWebSearchTool(WebSearchTool):
    name: str = "giftia_web_search_firecrawl"
    description: str = (
        "A web search tool based on Firecrawl Search API, used to retrieve web "
        "pages related to the user's query."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required. Search query."},
                "limit": {
                    "type": "integer",
                    "description": "Optional. Number of results to return. Range: 1-100. Default is 5.",
                },
                "location": {
                    "type": "string",
                    "description": "Optional. Geographic location for search results.",
                },
                "country": {
                    "type": "string",
                    "description": 'Optional. Country code for search results, for example "US" or "CN".',
                },
                "timeout": {
                    "type": "integer",
                    "description": "Optional. Request timeout in milliseconds.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        payload = {
            "query": kwargs["query"],
            "limit": kwargs.get("limit", 5),
            "sources": ["web"],
        }
        for key in ("location", "country", "timeout"):
            if kwargs.get(key):
                payload[key] = kwargs[key]
        data = await self.request_json(
            "POST", "https://api.firecrawl.dev/v2/search", json=payload
        )
        if data.get("success") is False:
            raise WebSearchError("Firecrawl 拒绝了搜索请求")
        path = ("data", "web") if isinstance(data.get("data"), dict) else ("data",)
        return format_web_results(
            result_rows(data, *path),
            snippet_fields=("description", "snippet", "markdown"),
        )


@dataclass
class FirecrawlExtractWebPageTool(WebSearchTool):
    name: str = "giftia_firecrawl_extract_web_page"
    description: str = "Extract the content of a web page using Firecrawl."
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Required. A URL to extract content from.",
                },
                "format": {
                    "type": "string",
                    "description": 'Optional. Output format, one of "markdown", "html", "rawHtml", "summary". Default is "markdown".',
                },
                "only_main_content": {
                    "type": "boolean",
                    "description": "Optional. Whether to extract only the main page content. Default is true.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Optional. Request timeout in milliseconds.",
                },
                "max_age": {
                    "type": "integer",
                    "description": "Optional. Maximum cache age in milliseconds.",
                },
            },
            "required": ["url"],
        }
    )

    async def _run(self, **kwargs) -> str:
        url = kwargs["url"].strip()
        output_format = kwargs.get("format", "markdown")
        if output_format not in ("markdown", "html", "rawHtml", "summary"):
            output_format = "markdown"
        payload = {
            "url": url,
            "formats": [output_format],
            "onlyMainContent": kwargs.get("only_main_content", True),
        }
        for name, field in (("timeout", "timeout"), ("max_age", "maxAge")):
            if kwargs.get(name) is not None:
                payload[field] = kwargs[name]
        data = await self.request_json(
            "POST", "https://api.firecrawl.dev/v2/scrape", json=payload
        )
        if data.get("success") is False:
            raise WebSearchError("Firecrawl 拒绝了正文提取请求")
        result = data.get("data")
        if isinstance(result, dict) and (content := result.get(output_format)):
            return f"URL: {result.get('url') or url}\nContent: {content}"
        return "Error: Firecrawl did not return any page content."
