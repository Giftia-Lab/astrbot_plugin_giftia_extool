from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchTool, format_web_results, result_rows


@dataclass
class BraveWebSearchTool(WebSearchTool):
    name: str = "giftia_web_search_brave"
    description: str = "A web search tool based on Brave Search API."
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required. Search query."},
                "count": {
                    "type": "integer",
                    "description": "Optional. Number of results to return. Range: 1-20.",
                },
                "country": {
                    "type": "string",
                    "description": 'Optional. Country code for region-specific results, for example "US" or "CN".',
                },
                "search_lang": {
                    "type": "string",
                    "description": 'Optional. Brave language code, for example "zh-hans" or "en".',
                },
                "freshness": {
                    "type": "string",
                    "description": 'Optional. One of "day", "week", "month", "year".',
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        payload = {
            "q": kwargs["query"],
            "count": max(1, min(int(kwargs.get("count", 10)), 20)),
            "country": kwargs.get("country", "US"),
            "search_lang": kwargs.get("search_lang", "zh-hans"),
        }
        freshness_codes = {"day": "pd", "week": "pw", "month": "pm", "year": "py"}
        if freshness := freshness_codes.get(kwargs.get("freshness")):
            payload["freshness"] = freshness

        data = await self.request_json(
            "GET",
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json"},
            key_headers={"X-Subscription-Token": ""},
            params=payload,
        )
        return format_web_results(
            result_rows(data, "web", "results"), snippet_fields=("description",)
        )
