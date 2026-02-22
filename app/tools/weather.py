from __future__ import annotations

from typing import Any, Dict, Optional, Type

from cachetools import TTLCache
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from app.core.exceptions import ToolExecutionError
from app.tools.http import HttpConfig, build_async_client, get_json
from app.tools.sync_base import SyncBaseTool


class WeatherInput(BaseModel):
    location: str = Field(..., description="City name (optionally with country/region)")
    temperature_unit: str = Field(default="celsius", description="celsius or fahrenheit")
    wind_speed_unit: str = Field(default="kmh", description="kmh, ms, mph, or kn")
    timezone: str = Field(default="auto", description="Timezone string or 'auto'")


class OpenMeteoWeatherTool(SyncBaseTool):
    name: str = "weather"
    description: str = (
        "Get current weather for a given location using Open-Meteo (no API key required). "
        "Returns temperature, wind, and weather code along with resolved location."
    )
    args_schema: Type[BaseModel] = WeatherInput

    def _run(
        self,
        location: str,
        temperature_unit: str = "celsius",
        wind_speed_unit: str = "kmh",
        timezone: str = "auto",
    ) -> Dict[str, Any]:
        import httpx

        # 1) geocode (sync)
        with httpx.Client(timeout=10.0) as client:
            geo = client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": location, "count": 1, "language": "en", "format": "json"},
            ).json()

        results = (geo or {}).get("results") or []
        if not results:
            return {"error": f"Could not geocode location: {location}"}

        r0 = results[0]
        lat, lon = r0["latitude"], r0["longitude"]
        resolved = ", ".join([p for p in [r0.get("name"), r0.get("admin1"), r0.get("country")] if p])

        # 2) current weather (sync)
        with httpx.Client(timeout=10.0) as client:
            wx = client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,weather_code,wind_speed_10m",
                    "temperature_unit": temperature_unit,
                    "wind_speed_unit": wind_speed_unit,
                    "timezone": timezone,
                },
            ).json()

        cur = (wx or {}).get("current") or {}
        return {
            "location_input": location,
            "location_resolved": resolved,
            "latitude": lat,
            "longitude": lon,
            "current": cur,
        }

    async def _geocode(self, location: str) -> Dict[str, Any]:
        key = location.strip().lower()
        if key in self._geocode_cache:
            return self._geocode_cache[key]

        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": location, "count": 1, "language": "en", "format": "json"}
        async with build_async_client(HttpConfig()) as client:
            payload = await get_json(client, url, params=params)
        results = payload.get("results") or []
        if not results:
            raise ToolExecutionError(f"Could not geocode location: {location}")
        first = results[0]
        resolved = {
            "name": first.get("name"),
            "country": first.get("country"),
            "admin1": first.get("admin1"),
            "latitude": first.get("latitude"),
            "longitude": first.get("longitude"),
        }
        self._geocode_cache[key] = resolved
        return resolved
