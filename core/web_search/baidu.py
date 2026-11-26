from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchTool, format_web_results, result_rows


@dataclass
class BaiduWebSearchTool(WebSearchTool):
    name: str = "giftia_web_search_baidu"
    description: str = (
        "A web search tool based on Baidu AI Search. "
        "Use this for real-time web retrieval when Baidu AI Search is configured."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required. Search query."},
                "top_k": {
                    "type": "integer",
                    "description": "Optional. Number of web results to return. Maximum 50. Default is 10.",
                },
                "search_recency_filter": {
                    "type": "string",
                    "description": 'Optional. One of "week", "month", "semiyear", "year".',
                },
                "site": {
                    "type": "string",
                    "description": "Optional. Restrict search to specific sites, separated by commas.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        top_k = max(1, min(int(kwargs.get("top_k", 10)), 50))
        payload = {
            "messages": [{"role": "user", "content": kwargs["query"][:72]}],
            "search_source": "baidu_search_v2",
            "resource_type_filter": [{"type": "web", "top_k": top_k}],
        }
        recency = kwargs.get("search_recency_filter")
        if recency in ("week", "month", "semiyear", "year"):
            payload["search_recency_filter"] = recency
        site = str(kwargs.get("site") or "")
        sites = [
            domain.strip()
            for domain in site.replace("|", ",").split(",")
            if domain.strip()
        ]
        if sites:
            payload["search_filter"] = {"match": {"site": sites[:100]}}

        auth = f"Bearer {self.api_key}"
        data = await self.request_json(
            "POST",
            "https://qianfan.baidubce.com/v2/ai_search/web_search",
            headers={"Authorization": auth, "X-Appbuilder-Authorization": auth},
            json=payload,
        )
        return format_web_results(
            result_rows(data, "references"), snippet_fields=("content",)
        )
