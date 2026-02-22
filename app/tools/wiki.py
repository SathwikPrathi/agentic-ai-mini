from __future__ import annotations

from typing import Any, Dict, Type

from cachetools import TTLCache
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.exceptions import ToolExecutionError
from app.tools.http import HttpConfig, build_async_client, get_json


class WikiInput(BaseModel):
    query: str = Field(..., description="Topic/title to look up")
    sentences: int = Field(default=5, ge=1, le=20, description="How many sentences to return")


class WikipediaSummaryTool(BaseTool):
    name: str = "wikipedia_summary"
    description: str = "Fetch a short summary about a topic from Wikipedia's REST API."
    args_schema: Type[BaseModel] = WikiInput

    _cache: TTLCache = TTLCache(maxsize=512, ttl=60 * 60 * 24)  # 24h

    def _run(self, query: str, sentences: int = 5) -> Dict[str, Any]:
        import asyncio

        return asyncio.run(self._arun(query=query, sentences=sentences))

    async def _arun(self, query: str, sentences: int = 5) -> Dict[str, Any]:
        key = f"{query.strip().lower()}::{sentences}"
        if key in self._cache:
            return self._cache[key]

        try:
            # First try the REST summary endpoint; it expects a page title.
            title = query.strip().replace(" ", "_")
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
            async with build_async_client(HttpConfig()) as client:
                payload = await get_json(client, url)

            extract = payload.get("extract") or ""
            # Naive sentence trimming to keep dependency-free.
            trimmed = ". ".join([s for s in extract.split(". ") if s][:sentences]).strip()
            if trimmed and not trimmed.endswith("."):
                trimmed += "."

            result = {
                "title": payload.get("title"),
                "description": payload.get("description"),
                "summary": trimmed or extract,
                "source_url": (payload.get("content_urls") or {}).get("desktop", {}).get("page"),
            }
            self._cache[key] = result
            return result
        except Exception as e:  # noqa: BLE001
            raise ToolExecutionError(f"Wikipedia summary tool failed: {e}") from e
