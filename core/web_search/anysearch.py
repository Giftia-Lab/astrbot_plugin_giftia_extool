import json
from typing import ClassVar

from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchError, WebSearchTool, format_web_results, result_rows


@dataclass
class AnySearchWebSearchTool(WebSearchTool):
    """Web search tool powered by the AnySearch API."""

    name: str = "giftia_web_search_anysearch"
    description: str = (
        "A web search tool powered by AnySearch. Supports general web search and "
        "16 vertical domains: academic(search/biomedical/citation/preprint/dataset), "
        "business(company/jobs/people/trade), code(doc/snippet), "
        "energy(production/electricity), environment(aqi), "
        "finance(quote/fundamental/news/calendar/screen/macro), film(torrent), "
        "gaming(esports/store), health(drug/stats/trial), ip(global), "
        "legal(case/statute/legislation), resource(image), "
        "security(vuln/noise/intel/scan), social_media, "
        "travel(flight/flight_status), agriculture(fao), and general web search."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required. Search query."},
                "max_results": {
                    "type": "integer",
                    "description": "Optional. The maximum number of results to return. Default is 10. Range is 1-10.",
                },
                "tag": {
                    "type": "string",
                    "description": (
                        'Optional. Domain capability tag in "{domain}.{subdomain}" form, '
                        'for example "finance.quote" or "academic.search". '
                        "Available domains: general, resource, social_media, finance(quote/fundamental/news/calendar/screen/macro), "
                        "academic(search/biomedical/citation/preprint/dataset), legal(case/statute/legislation), "
                        "health(drug/stats/trial), business(company/jobs/people/trade), "
                        "security(vuln/noise/intel/scan), ip(global), code(doc/snippet), "
                        "energy(production/electricity), environment(aqi), agriculture(fao), "
                        "travel(flight/flight_status), film(torrent), gaming(esports/store). "
                        "Omit for general web search."
                    ),
                },
                "zone": {
                    "type": "string",
                    "description": 'Optional. Result region, must be one of "cn", "intl", "global".',
                },
                "language": {
                    "type": "string",
                    "description": 'Optional. Preferred result language, for example "zh-CN" or "en".',
                },
                "params": {
                    "type": "object",
                    "description": (
                        "Optional. Extra parameters required by specific vertical tags. "
                        'Examples: {"symbol": "AAPL", "type": "stock"} for finance.quote, '
                        '{"type": "cve", "value": "CVE-2021-44228"} for security.vuln, '
                        '{"doi": "10.1038/s41586-021-03819-2"} for academic.search, '
                        '{"departure": "SHA", "arrival": "PEK", "date": "2026-09-10"} for travel.flight.'
                    ),
                },
            },
            "required": ["query"],
        }
    )
    requires_api_key: ClassVar[bool] = False

    async def _run(self, **kwargs) -> str:
        try:
            max_results = int(kwargs.get("max_results", 10))
        except (TypeError, ValueError):
            max_results = 10
        payload = {
            "query": kwargs["query"],
            "max_results": max(1, min(max_results, 10)),
            "format": "json",
        }
        for field in ("tag", "language"):
            value = str(kwargs.get(field) or "").strip()
            if value:
                payload[field] = value
        if kwargs.get("zone") in ("cn", "intl", "global"):
            payload["zone"] = kwargs["zone"]
        if isinstance(kwargs.get("params"), dict):
            payload["params"] = kwargs["params"]

        data = await self.request_json(
            "POST", "https://api.anysearch.com/v1/search", json=payload
        )
        if data.get("code") not in (None, 0):
            raise WebSearchError("AnySearch 拒绝了搜索请求")
        path = ("data", "results") if data.get("data") else ("results",)
        rows = result_rows(data, *path)
        for row in rows:
            snippet = row.get("snippet") or row.get("content") or ""
            extras = []
            # Vertical search results may store relevant information outside the snippet.
            for field, value in row.items():
                if (
                    field in {"title", "url", "snippet", "content", "favicon"}
                    or value is None
                ):
                    continue
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                extras.append(f"{field}: {value}")
            row["snippet"] = "\n".join([str(snippet), *extras]).strip()
        return format_web_results(rows)
