from datetime import date, timedelta

from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchTool, format_web_results, result_rows


@dataclass
class TavilyWebSearchTool(WebSearchTool):
    name: str = "giftia_web_search_tavily"
    description: str = (
        "A web search tool that uses Tavily to search the web for relevant content. "
        "Ideal for gathering current information, news, and detailed web content analysis."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required. Search query."},
                "max_results": {
                    "type": "integer",
                    "description": "Optional. The maximum number of results to return. Default is 7. Range is 5-20.",
                },
                "search_depth": {
                    "type": "string",
                    "description": 'Optional. The depth of the search, must be one of "basic", "advanced". Default is "basic".',
                },
                "topic": {
                    "type": "string",
                    "description": 'Optional. The topic of the search, must be one of "general", "news". Default is "general".',
                },
                "days": {
                    "type": "integer",
                    "description": 'Optional. The number of days back from the current date to include in the search results. This only applies when topic is "news".',
                },
                "time_range": {
                    "type": "string",
                    "description": 'Optional. The time range back from the current date to include in the search results. Must be one of "day", "week", "month", "year".',
                },
                "start_date": {
                    "type": "string",
                    "description": "Optional. The start date for the search results in the format YYYY-MM-DD.",
                },
                "end_date": {
                    "type": "string",
                    "description": "Optional. The end date for the search results in the format YYYY-MM-DD.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        search_depth = kwargs.get("search_depth", "basic")
        if search_depth not in ("basic", "advanced"):
            search_depth = "basic"
        topic = kwargs.get("topic", "general")
        if topic not in ("general", "news"):
            topic = "general"
        payload = {
            "query": kwargs["query"],
            "max_results": kwargs.get("max_results", 7),
            "search_depth": search_depth,
            "topic": topic,
        }

        start_date = str(kwargs.get("start_date") or "").strip()
        end_date = str(kwargs.get("end_date") or "").strip()
        time_range = kwargs.get("time_range")
        if start_date or end_date:
            if start_date:
                payload["start_date"] = start_date
            if end_date:
                payload["end_date"] = end_date
        elif time_range in ("day", "week", "month", "year"):
            payload["time_range"] = time_range
        elif topic == "news":
            # Translate the legacy news days argument to a publish date filter.
            days = int(kwargs.get("days", 3))
            payload["start_date"] = (date.today() - timedelta(days=days)).isoformat()

        data = await self.request_json(
            "POST", "https://api.tavily.com/search", json=payload
        )
        return format_web_results(
            result_rows(data, "results"), snippet_fields=("content",)
        )


@dataclass
class TavilyExtractWebPageTool(WebSearchTool):
    name: str = "giftia_tavily_extract_web_page"
    description: str = "Extract the content of a web page using Tavily."
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Required. A URL to extract content from.",
                },
                "extract_depth": {
                    "type": "string",
                    "description": 'Optional. The depth of the extraction, must be one of "basic", "advanced". Default is "basic".',
                },
            },
            "required": ["url"],
        }
    )

    async def _run(self, **kwargs) -> str:
        url = kwargs["url"].strip()
        extract_depth = kwargs.get("extract_depth", "basic")
        if extract_depth not in ("basic", "advanced"):
            extract_depth = "basic"
        data = await self.request_json(
            "POST",
            "https://api.tavily.com/extract",
            json={"urls": [url], "extract_depth": extract_depth},
        )
        pages = [
            f"URL: {row.get('url', url)}\nContent: {row.get('raw_content', 'No content')}"
            for row in result_rows(data, "results")
        ]
        return "\n".join(pages) or "Error: Tavily did not return any page content."
