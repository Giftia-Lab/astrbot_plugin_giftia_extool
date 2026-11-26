from urllib.parse import urlsplit

from pydantic import Field
from pydantic.dataclasses import dataclass

from .base import WebSearchTool, format_web_results, result_rows


@dataclass
class DeepSeekWebSearchTool(WebSearchTool):
    name: str = "giftia_web_search_deepseek"
    description: str = (
        "Search the web with DeepSeek and return page summaries or full text. "
        "Use giftia_deepseek_fetch_web_page to read a known URL."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": (
                        "Search query, 1-128 Unicode characters including filters, "
                        "not all whitespace. Filters can be combined. Examples:\n"
                        "Find DeepSeek API references on GitHub or Hugging Face -> "
                        'DeepSeek "API reference" site:github.com OR site:huggingface.co\n'
                        "Find Chinese or English DeepSeek news published after 2026-01-01 "
                        "and before 2027-01-01 -> "
                        "DeepSeek news lang:zh,en after:2026-01-01 before:2027-01-01\n"
                        "Find DeepSeek information excluding ads, example.com and the phrase "
                        '"release notes" -> DeepSeek -Ads -site:example.com -"release notes"\n'
                        "Date filters accept YYYY or YYYY-MM-DD."
                    ),
                },
                "count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                    "description": "Optional. Number of results, 1-50. Default is 10.",
                },
                "ori_question": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 128,
                    "description": "Optional. Original user question, 1-128 Unicode characters.",
                },
                "need_content": {
                    "type": "boolean",
                    "default": False,
                    "description": "Optional. Include full page content in results. Default is false.",
                },
            },
            "required": ["query"],
        }
    )

    async def _run(self, **kwargs) -> str:
        query = kwargs["query"]
        if len(query) > 128:
            return (
                "Error: query must be a non-blank string of 1-128 Unicode characters."
            )
        count = kwargs.get("count", 10)
        if type(count) is not int or not 1 <= count <= 50:
            return "Error: count must be an integer between 1 and 50."
        ori_question = kwargs.get("ori_question")
        if ori_question is not None and (
            not isinstance(ori_question, str) or not 1 <= len(ori_question) <= 128
        ):
            return "Error: ori_question must be a string of 1-128 Unicode characters."
        need_content = kwargs.get("need_content", False)
        if not isinstance(need_content, bool):
            return "Error: need_content must be a boolean."

        payload = {"query": query, "count": count, "need_content": need_content}
        if ori_question is not None:
            payload["ori_question"] = ori_question
        data = await self.request_json(
            "POST", "https://api.deepseek.com/v1/tools/search", json=payload
        )
        rows = result_rows(data, "results")
        for row in rows:
            snippet = row.get("summary") or row.get("snippet") or ""
            if need_content and (content := row.get("content")):
                snippet = "\n\n".join(filter(None, [snippet, content]))
            row["snippet"] = snippet
        return format_web_results(rows)


@dataclass
class DeepSeekFetchWebPageTool(WebSearchTool):
    name: str = "giftia_deepseek_fetch_web_page"
    description: str = (
        "Fetch a single web page using DeepSeek and return its title and Markdown content. "
        "Use this to read a known URL, including a page found through web search."
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 8192,
                    "description": "Required. HTTP or HTTPS URL with a host, no embedded credentials, and at most 8192 characters.",
                },
            },
            "required": ["url"],
        }
    )

    async def _run(self, **kwargs) -> str:
        url = kwargs["url"]
        if len(url) > 8192:
            return "Error: url must be a string of 1-8192 characters."
        try:
            parsed = urlsplit(url)
            # urllib.parse validates the port when it is read.
            _ = parsed.port
            valid_url = (
                parsed.scheme in {"http", "https"}
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and not any(char.isspace() for char in url)
            )
        except ValueError:
            valid_url = False
        if not valid_url:
            return "Error: url must be an HTTP or HTTPS URL with a host and no embedded credentials."

        data = await self.request_json(
            "POST", "https://api.deepseek.com/v1/tools/fetch", json={"url": url}
        )
        if not data.get("content"):
            return "Error: DeepSeek did not return any page content."
        return f"URL: {url}\nTitle: {data.get('title', '')}\nContent: {data['content']}"
