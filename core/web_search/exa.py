from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchTool, format_web_results, result_rows


@dataclass
class ExaWebSearchTool(WebSearchTool):
    """Web search tool powered by the Exa Search API."""

    name: str = "giftia_web_search_exa"
    description: str = (
        "A web search tool powered by Exa, an AI-native search engine. "
        "Supports keyword and semantic search with domain, date, and category filters."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required. Search query."},
                "num_results": {
                    "type": "integer",
                    "description": "Optional. Number of results to return. Default is 10.",
                },
                "type": {
                    "type": "string",
                    "description": (
                        'Optional. Search type. One of "auto", "keyword", "neural". '
                        'Default is "auto".'
                    ),
                },
                "category": {
                    "type": "string",
                    "description": (
                        "Optional. Category filter. One of "
                        '"company", "research paper", "news", "github", '
                        '"tweet", "personal site", "pdf", "linkedin profile".'
                    ),
                },
                "include_domains": {
                    "type": "string",
                    "description": "Optional. Comma-separated domains to restrict results to.",
                },
                "exclude_domains": {
                    "type": "string",
                    "description": "Optional. Comma-separated domains to exclude from results.",
                },
                "start_published_date": {
                    "type": "string",
                    "description": "Optional. Start date filter in ISO 8601 format (e.g. 2024-01-01T00:00:00.000Z).",
                },
                "end_published_date": {
                    "type": "string",
                    "description": "Optional. End date filter in ISO 8601 format.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        try:
            num_results = int(kwargs.get("num_results", 10))
        except (TypeError, ValueError):
            num_results = 10
        search_type = kwargs.get("type", "auto")
        if search_type not in ("auto", "keyword", "neural"):
            search_type = "auto"
        payload = {
            "query": kwargs["query"],
            "numResults": max(1, num_results),
            "type": search_type,
            "contents": {"text": {"maxCharacters": 500}},
        }
        for name, field in (
            ("include_domains", "includeDomains"),
            ("exclude_domains", "excludeDomains"),
        ):
            raw = str(kwargs.get(name) or "").strip()
            if raw:
                payload[field] = [
                    domain.strip() for domain in raw.split(",") if domain.strip()
                ]
        for name, field in (
            ("category", "category"),
            ("start_published_date", "startPublishedDate"),
            ("end_published_date", "endPublishedDate"),
        ):
            if kwargs.get(name):
                payload[field] = kwargs[name]

        data = await self.request_json(
            "POST",
            "https://api.exa.ai/search",
            headers={"x-api-key": self.api_key},
            json=payload,
        )
        return format_web_results(
            result_rows(data, "results"),
            snippet_fields=("text", "highlights", "summary"),
        )


@dataclass
class ExaGetContentsTool(WebSearchTool):
    """Extract full page content from URLs using the Exa Contents API."""

    name: str = "giftia_exa_get_contents"
    description: str = "Extract the content of a web page using Exa."
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Required. A URL to extract content from.",
                },
                "max_characters": {
                    "type": "integer",
                    "description": "Optional. Maximum number of characters to return. Default is 3000.",
                },
            },
            "required": ["url"],
        }
    )

    async def _run(self, **kwargs) -> str:
        url = kwargs["url"].strip()
        try:
            max_characters = int(kwargs.get("max_characters", 3000))
        except (TypeError, ValueError):
            max_characters = 3000

        data = await self.request_json(
            "POST",
            "https://api.exa.ai/contents",
            headers={"x-api-key": self.api_key},
            json={"ids": [url], "text": {"maxCharacters": max_characters}},
        )
        pages = [
            f"URL: {row.get('url', url)}\nContent: {row.get('text', 'No content')}"
            for row in result_rows(data, "results")
        ]
        return "\n".join(pages) or "Error: Exa did not return any page content."
