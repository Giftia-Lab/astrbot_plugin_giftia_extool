from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchTool, format_web_results, result_rows


@dataclass
class BochaWebSearchTool(WebSearchTool):
    name: str = "giftia_web_search_bocha"
    description: str = (
        "A web search tool based on Bocha Search API, used to retrieve web pages "
        "related to the user's query."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Required. User's search query.",
                },
                "freshness": {
                    "type": "string",
                    "description": 'Optional. Time range of the search. Recommended value is "noLimit".',
                },
                "summary": {
                    "type": "boolean",
                    "description": "Optional. Whether to include a text summary for each search result.",
                },
                "include": {
                    "type": "string",
                    "description": "Optional. Domains to include in the search, separated by | or ,.",
                },
                "exclude": {
                    "type": "string",
                    "description": "Optional. Domains to exclude from the search, separated by | or ,.",
                },
                "count": {
                    "type": "integer",
                    "description": "Optional. Number of search results to return. Range: 1-50.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        payload = {
            "query": kwargs["query"],
            "count": kwargs.get("count", 10),
            "summary": bool(kwargs.get("summary", False)),
        }
        for key in ("freshness", "include", "exclude"):
            if kwargs.get(key):
                payload[key] = kwargs[key]

        data = await self.request_json(
            "POST",
            "https://api.bochaai.com/v1/web-search",
            headers={
                "Accept-Encoding": "gzip, deflate",
            },
            json=payload,
        )
        return format_web_results(
            result_rows(data, "data", "webPages", "value"),
            title_field="name",
            snippet_fields=("summary", "snippet")
            if payload["summary"]
            else ("snippet",),
        )
