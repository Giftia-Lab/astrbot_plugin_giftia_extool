import asyncio
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import monotonic
from typing import ClassVar

import aiohttp
from astrbot.core.agent.tool import FunctionTool
from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass


class WebSearchError(Exception):
    """A provider error whose message can be shown to the model."""


class SearchKeyPool:
    """Round-robin credentials and cooldowns shared by one provider's tools."""

    def __init__(self, keys: tuple[str, ...] = ()) -> None:
        self.keys = keys
        self._index = 0
        self._cooldown_until: dict[str, float] = {}

    def take(self, *, exclude: str | None) -> str | None:
        """Select and advance to the next ready credential.

        Args:
            exclude: Credential already attempted by this request.

        Returns:
            The next eligible credential, if any.
        """
        now = monotonic()
        for _ in self.keys:
            key = self.keys[self._index]
            self._index = (self._index + 1) % len(self.keys)
            if key != exclude and self._cooldown_until.get(key, 0) <= now:
                return key
        return None

    def cool_down(self, key: str, retry_after: str | None) -> None:
        """Temporarily skip a throttled credential.

        Args:
            key: Credential used in the throttled request.
            retry_after: Optional delay or HTTP date from the provider.
        """
        seconds = 0.0
        if retry_after:
            try:
                seconds = float(int(retry_after))
            except (ValueError, OverflowError):
                try:
                    reset_at = parsedate_to_datetime(retry_after)
                    seconds = (reset_at - datetime.now(timezone.utc)).total_seconds()
                except (TypeError, ValueError, OverflowError):
                    pass
        until = monotonic() + (seconds if seconds > 0 else 30.0)
        self._cooldown_until[key] = max(self._cooldown_until.get(key, 0), until)


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class WebSearchTool(FunctionTool):
    key_pool: SearchKeyPool = Field(
        default_factory=SearchKeyPool, repr=False, exclude=True
    )
    requires_api_key: ClassVar[bool] = True

    async def call(self, context, **kwargs) -> str:
        """Execute a provider operation and return a result or a safe error.

        Args:
            context: AstrBot tool execution context.
            **kwargs: Arguments from the operation's tool schema.

        Returns:
            Web results, extracted text, or a failure message.
        """
        if self.requires_api_key and not self.key_pool.keys:
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
        self,
        method: str,
        url: str,
        *,
        headers: dict | None = None,
        key_headers: dict[str, str] | None = None,
        key_in_query: bool = False,
        **kwargs,
    ) -> dict:
        """Send an HTTP request to an operation's provider endpoint.

        Args:
            method: HTTP method for the request.
            url: Fixed URL of the provider API.
            headers: Additional headers for the request.
            key_headers: Credential header names and value prefixes, with Bearer auth by default.
            key_in_query: Send the credential as the api_key query parameter.
            **kwargs: JSON payload, query string, or request timeout.

        Returns:
            JSON object returned by the provider.

        Raises:
            WebSearchError: If the provider returns an error or a malformed object.
        """
        if key_headers is None:
            key_headers = {"Authorization": "Bearer "}

        async def request_with_keys(session: aiohttp.ClientSession) -> dict:
            previous_key = None
            for _ in range(2):
                key = self.key_pool.take(exclude=previous_key)
                if key is None and self.key_pool.keys:
                    break

                request_headers = dict(headers or {})
                request_options = kwargs.copy()
                if key and key_in_query:
                    request_options["params"] = {
                        **kwargs.get("params", {}),
                        "api_key": key,
                    }
                elif key:
                    request_headers.update(
                        {name: prefix + key for name, prefix in key_headers.items()}
                    )

                async with session.request(
                    method,
                    url,
                    headers=request_headers,
                    allow_redirects=False,
                    **request_options,
                ) as response:
                    if response.status == 429 and key is not None:
                        self.key_pool.cool_down(
                            key, response.headers.get("Retry-After")
                        )
                        previous_key = key
                        continue
                    if response.status != 200:
                        raise WebSearchError(f"HTTP {response.status}")
                    data = await response.json()
                if not isinstance(data, dict):
                    raise WebSearchError("供应商返回了无效的结果")
                return data
            raise WebSearchError("网页搜索 API 密钥触发限流，请稍后重试")

        async with aiohttp.ClientSession(
            trust_env=True, cookie_jar=aiohttp.DummyCookieJar()
        ) as session:
            timeout = kwargs.get("timeout", session.timeout)
            if isinstance(timeout, aiohttp.ClientTimeout):
                timeout = timeout.total
            return await asyncio.wait_for(
                request_with_keys(session),
                timeout=timeout if timeout and timeout > 0 else None,
            )


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
