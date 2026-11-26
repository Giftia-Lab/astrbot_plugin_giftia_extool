import asyncio
import json
from typing import ClassVar

import aiohttp
from pydantic import Field
from pydantic.dataclasses import dataclass

from astrbot.core.agent.tool import FunctionTool


class WebSearchError(Exception):
    """A provider error whose message can be shown to the model."""


@dataclass
class WebSearchTool(FunctionTool):
    api_key: str = Field(default="", repr=False)
    requires_api_key: ClassVar[bool] = True

    async def call(self, context, **kwargs) -> str:
        """Execute a provider operation and return a result or a safe error.

        Args:
            context: AstrBot tool execution context.
            **kwargs: Arguments from the operation's tool schema.

        Returns:
            Web results, extracted text, or a failure message.
        """
        if self.requires_api_key and not self.api_key:
            return "请在 Giftia ExTool 插件配置中填写网页搜索 API 密钥。"

        for param in self.parameters["required"]:
            value = kwargs.get(param)
            if not isinstance(value, str) or not value.strip():
                return f"Error: {param} must be a non-empty string."

        try:
            return await self._run(**kwargs)
        except WebSearchError as exc:
            return f"网页工具请求失败（{exc}）。"
        except asyncio.TimeoutError:
            return "网页工具请求超时，请稍后重试。"
        except aiohttp.ClientError:
            # Transport exceptions can include the request URL and API key.
            return "网页工具请求失败，请检查供应商配置或稍后重试。"
        except (TypeError, ValueError, OverflowError):
            return "网页工具请求失败，参数或供应商响应格式无效。"

    async def _run(self, **kwargs) -> str:
        raise NotImplementedError

    async def request_json(
        self, method: str, url: str, *, headers: dict | None = None, **kwargs
    ) -> dict:
        """Send an HTTP request to an operation's provider endpoint.

        Args:
            method: HTTP method for the request.
            url: Fixed URL of the provider API.
            headers: Custom headers when the provider uses different credentials.
            **kwargs: JSON payload, query string, or request timeout.

        Returns:
            JSON object returned by the provider.

        Raises:
            WebSearchError: If the provider returns an error or a malformed object.
        """
        if headers is None:
            headers = (
                {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.request(
                method, url, headers=headers, allow_redirects=False, **kwargs
            ) as response:
                if response.status != 200:
                    raise WebSearchError(f"HTTP {response.status}")
                data = await response.json()
        if not isinstance(data, dict):
            raise WebSearchError("供应商返回了无效的结果")
        return data


def result_rows(data: dict, *path: str) -> list[dict]:
    """Read the provider's list of results from a nested response.

    Args:
        data: Provider response object.
        *path: Object keys that lead to the list of results.

    Returns:
        Result objects in provider order. An absent list yields no results.

    Raises:
        WebSearchError: If an element of the response path has the wrong type.
    """
    rows = data
    for key in path:
        if rows is None:
            return []
        if not isinstance(rows, dict):
            raise WebSearchError("供应商返回了无效的结果")
        rows = rows.get(key)
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise WebSearchError("供应商返回了无效的结果")
    return [row for row in rows if isinstance(row, dict)]


def format_web_results(
    rows: list[dict],
    *,
    title_field: str = "title",
    url_field: str = "url",
    snippet_fields: tuple[str, ...] = ("snippet",),
) -> str:
    """Return page titles, URLs and snippets for the model.

    Args:
        rows: Search hits from the provider.
        title_field: Provider field holding the page title.
        url_field: Provider field holding the page URL.
        snippet_fields: Candidate snippet fields in priority order.

    Returns:
        JSON search results containing titles, URLs and snippets.
    """
    results = []
    for row in rows:
        url = row.get(url_field)
        if not isinstance(url, str) or not url.strip():
            continue
        title = row.get(title_field)
        snippet = ""
        for field in snippet_fields:
            value = row.get(field)
            if field == "highlights" and isinstance(value, list):
                value = next(
                    (part for part in value if isinstance(part, str) and part.strip()),
                    "",
                )
            if isinstance(value, str) and value.strip():
                snippet = value
                break
        results.append(
            {
                "title": title if isinstance(title, str) else "",
                "url": url,
                "snippet": snippet,
            }
        )
    return json.dumps({"results": results}, ensure_ascii=False)
