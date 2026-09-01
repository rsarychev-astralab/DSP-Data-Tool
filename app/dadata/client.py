import asyncio

import httpx
from fastapi import HTTPException

from app.config import dadata_api_key

SUGGEST_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/party"
FIND_URL = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"


def auth_headers() -> dict[str, str]:
    api_key = dadata_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="DADATA_API_KEY не задан в окружении")
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {api_key}",
    }


async def fetch_party(client: httpx.AsyncClient, inn: str) -> dict | None:
    response = await client.post(
        FIND_URL,
        headers=auth_headers(),
        json={"query": inn},
    )
    if response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Превышен лимит запросов DaData. Попробуйте позже или уменьшите файл.",
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"DaData error {response.status_code}",
        )
    suggestions = (response.json() or {}).get("suggestions") or []
    return suggestions[0] if suggestions else None


async def fetch_party_with_retry(client: httpx.AsyncClient, inn: str) -> dict | None:
    try:
        return await fetch_party(client, inn)
    except HTTPException as exc:
        if exc.status_code == 502:
            await asyncio.sleep(0.4)
            return await fetch_party(client, inn)
        raise


async def suggest_party(query: str, count: int) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            SUGGEST_URL,
            headers=auth_headers(),
            json={"query": query, "count": count},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"DaData error {response.status_code}",
        )

    return response.json()
