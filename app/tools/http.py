from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass(frozen=True)
class HttpConfig:
    timeout_s: float = 12.0
    user_agent: str = "agentic-ai-mini-project/1.0"


def build_async_client(config: HttpConfig) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=config.timeout_s,
        headers={"User-Agent": config.user_agent},
        follow_redirects=True,
    )


def build_sync_client(config: HttpConfig) -> httpx.Client:
    return httpx.Client(
        timeout=config.timeout_s,
        headers={"User-Agent": config.user_agent},
        follow_redirects=True,
    )


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(3))
async def get_json(client: httpx.AsyncClient, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    resp = await client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


@retry(wait=wait_exponential(multiplier=0.5, min=0.5, max=4), stop=stop_after_attempt(3))
def get_json_sync(client: httpx.Client, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    resp = client.get(url, params=params)
    resp.raise_for_status()
    return resp.json()
