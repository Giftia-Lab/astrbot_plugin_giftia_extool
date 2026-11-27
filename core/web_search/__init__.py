"""Provider tools adapted from AstrBot's built-in web search (AGPL-3.0-or-later)."""

from .anysearch import AnySearchWebSearchTool
from .baidu import BaiduWebSearchTool
from .base import SearchKeyPool, WebSearchTool
from .bocha import BochaWebSearchTool
from .brave import BraveWebSearchTool
from .deepseek import DeepSeekFetchWebPageTool, DeepSeekWebSearchTool
from .exa import ExaGetContentsTool, ExaWebSearchTool
from .firecrawl import FirecrawlExtractWebPageTool, FirecrawlWebSearchTool
from .serpapi import (
    SerpApiFinanceSearchTool,
    SerpApiImageSearchTool,
    SerpApiNewsSearchTool,
    SerpApiScholarSearchTool,
    SerpApiWebSearchTool,
)
from .tavily import TavilyExtractWebPageTool, TavilyWebSearchTool

_TOOLS_BY_PROVIDER: dict[str, tuple[type[WebSearchTool], ...]] = {
    "tavily": (TavilyWebSearchTool, TavilyExtractWebPageTool),
    "bocha": (BochaWebSearchTool,),
    "brave": (BraveWebSearchTool,),
    "firecrawl": (FirecrawlWebSearchTool, FirecrawlExtractWebPageTool),
    "baidu_ai_search": (BaiduWebSearchTool,),
    "exa": (ExaWebSearchTool, ExaGetContentsTool),
    "anysearch": (AnySearchWebSearchTool,),
    "deepseek": (DeepSeekWebSearchTool, DeepSeekFetchWebPageTool),
    "serpapi": (
        SerpApiWebSearchTool,
        SerpApiNewsSearchTool,
        SerpApiImageSearchTool,
        SerpApiFinanceSearchTool,
        SerpApiScholarSearchTool,
    ),
}


def build_web_search_tools(provider: str, api_keys: list[str]) -> list[WebSearchTool]:
    """Build the tools for the plugin's selected provider.

    Args:
        provider: Provider selected in the plugin settings.
        api_keys: Credentials shared by the selected provider's tools.

    Returns:
        Tool instances for the provider, or an empty list for an unknown provider.
    """
    keys = ()
    if isinstance(api_keys, list):
        keys = tuple(
            dict.fromkeys(
                key.strip() for key in api_keys if isinstance(key, str) and key.strip()
            )
        )
    key_pool = SearchKeyPool(keys)
    return [tool(key_pool=key_pool) for tool in _TOOLS_BY_PROVIDER.get(provider, ())]
