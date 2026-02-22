from __future__ import annotations

from typing import Any, Dict, Type

from cachetools import TTLCache
from pydantic import BaseModel, Field
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.exceptions import ToolExecutionError
from app.tools.http import HttpConfig, build_sync_client, get_json_sync
from app.tools.sync_base import SyncBaseTool


class TimeInput(BaseModel):
    timezone: str = Field(..., description="IANA timezone, e.g., 'Asia/Kolkata'")


class WorldTimeTool(SyncBaseTool):
    name: str = "time_in"
    description: str = "Get the current local time for a given IANA timezone using worldtimeapi.org"
    args_schema: Type[BaseModel] = TimeInput

    _cache: TTLCache = TTLCache(maxsize=256, ttl=30)

    def _run(self, timezone: str) -> dict:
        try:
            now = datetime.now(ZoneInfo(timezone))
            return {
                "timezone": timezone,
                "datetime": now.isoformat(),
                "date": now.date().isoformat(),
                "time": now.time().replace(microsecond=0).isoformat(),
                "utc_offset": now.strftime("%z"),
            }
        except Exception as e:
            return {"error": f"Invalid timezone '{timezone}': {e}"}
