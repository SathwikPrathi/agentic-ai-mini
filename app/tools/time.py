from __future__ import annotations

from typing import Any, Dict, Type

from cachetools import TTLCache
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.exceptions import ToolExecutionError
from app.tools.http import HttpConfig, build_async_client, get_json


class TimeInput(BaseModel):
    timezone: str = Field(..., description="IANA timezone, e.g., 'Asia/Kolkata'")


class WorldTimeTool(BaseTool):
    name: str = "time_in"
    description: str = "Get the current local time for a given IANA timezone using worldtimeapi.org"
    args_schema: Type[BaseModel] = TimeInput

    _cache: TTLCache = TTLCache(maxsize=256, ttl=30)

    def _run(self, timezone: str) -> Dict[str, Any]:
        import asyncio

        return asyncio.run(self._arun(timezone=timezone))

    async def _arun(self, timezone: str) -> Dict[str, Any]:
        key = timezone.strip()
        if key in self._cache:
            return self._cache[key]

        try:
            url = f"https://worldtimeapi.org/api/timezone/{key}"
            async with build_async_client(HttpConfig()) as client:
                payload = await get_json(client, url)
            result = {
                "timezone": payload.get("timezone"),
                "datetime": payload.get("datetime"),
                "utc_offset": payload.get("utc_offset"),
                "day_of_week": payload.get("day_of_week"),
            }
            self._cache[key] = result
            return result
        except Exception as e:  # noqa: BLE001
            raise ToolExecutionError(f"Time tool failed: {e}") from e
